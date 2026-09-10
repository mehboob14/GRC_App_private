"""Vendor register — reads, writes, and the implicit default engagement.

Section 1 of openspec/changes/week5-vendor-risk. The rules that live here rather
than in the database:

- **Every vendor has at least one engagement.** ``create_vendor`` writes the
  default in the same transaction (V10), so nothing downstream special-cases a
  vendor with no engagement.
- **Duplicate detection warns, it never blocks** (ER ¶90). Two real subsidiaries
  share a trading name; a unique constraint would refuse a legitimate record, so
  the near-matches come back on the created vendor and a person decides.
- **The vendor's tier / residual / grade / contract value are recomputed from its
  engagements**, never written directly. ``_recache`` is the only writer, and it
  takes the worst engagement so the register ranks on the worst case.

Nothing here advances a lifecycle: the twelve-stage machine is section 2, and a
vendor created now sits at ``requested`` until it lands.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core import ratelimit
from verity.core.config import get_settings
from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.modules.vendors import lifecycle, scoring
from verity.modules.vendors.models import (
    BUNDLE_BY_TIER,
    CONTACT_TYPES,
    DATA_CLASSIFICATIONS,
    DEFAULT_ENGAGEMENT_NAME,
    FINDING_SEVERITIES,
    LIFECYCLE_STATUSES,
    OPEN_FINDING_STATUSES,
    RISK_DOMAIN_LABELS,
    TIERS,
    VENDOR_TYPES,
    QuestionnaireQuestion,
    QuestionnaireTemplate,
    Vendor,
    VendorAssessment,
    VendorAssessmentResponse,
    VendorContact,
    VendorEngagement,
    VendorFinding,
    VendorPortalToken,
    VendorStage,
    VendorTieringAssessment,
    VendorTieringPolicy,
    VendorTransition,
)
from verity.shared.ids import uuid7

logger: Final = structlog.get_logger(__name__)

# -- shared rules (the client is served these; it never hardcodes them) -------

TIER_RANK: Final[dict[str, int]] = {tier: rank for rank, tier in enumerate(TIERS)}
"""Worst-first. ``critical`` is 0, so ``min`` over this picks the worst tier."""

_SNAPSHOT: Final[tuple[str, ...]] = (
    "name",
    "vendor_type",
    "lifecycle_status",
    "data_classification",
    "stores_pii",
    "business_owner_membership_id",
)

_ENGAGEMENT_SNAPSHOT: Final[tuple[str, ...]] = ("name", "status", "tier", "business_unit")

# Reader-facing copy reused across several raises in this module.
_VENDOR_GONE: Final = "This vendor no longer exists. It may have been deleted."
_ENGAGEMENT_GONE: Final = "This engagement no longer exists. It may have been deleted."
_STAGE_GONE: Final = (
    "This lifecycle stage no longer exists. The review may have moved on. "
    "Refresh the page to see where it is now."
)

_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|gmbh|plc|co|sa|bv|ag|pty)\b|[^a-z0-9]+"
)


def _fingerprint(name: str) -> str:
    """A comparable form of a trading name: lowercased, legal suffixes dropped.

    "Acme, Inc." and "ACME Corporation" both become "acme", which is what makes
    the duplicate warning fire on the case it exists for.
    """
    return _NOISE.sub("", name.lower())


def _domain(website: str | None) -> str | None:
    """The registrable-looking part of a URL, for matching two spellings of one site."""
    if not website:
        return None
    host = website.strip().lower()
    host = re.sub(r"^[a-z]+://", "", host).split("/")[0].split("?")[0]
    return re.sub(r"^www\.", "", host) or None


# -- views (returned to the router; never ORM rows) ---------------------------


@dataclass(frozen=True, slots=True)
class EngagementView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    service_description: str
    business_unit: str | None
    internal_owner_membership_id: uuid.UUID | None
    internal_owner_name: str | None
    tier: str | None
    status: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ContactView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    contact_type: str


@dataclass(frozen=True, slots=True)
class OwnershipView:
    business_owner_membership_id: uuid.UUID | None
    business_owner_name: str | None
    security_owner_membership_id: uuid.UUID | None
    security_owner_name: str | None
    relationship_owner_membership_id: uuid.UUID | None
    relationship_owner_name: str | None


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    """A vendor that looks like the one just saved. A warning, never a refusal."""

    id: uuid.UUID
    name: str
    reason: str


@dataclass(frozen=True)
class VendorView:
    id: uuid.UUID
    name: str
    vendor_type: str
    industry: str | None
    website: str | None
    business_unit: str | None
    services_provided: str
    stores_pii: bool
    data_location: str | None
    data_types_in_scope: list[str]
    data_classification: str | None
    lifecycle_status: str
    tier: str | None
    current_residual_score: float | None
    current_grade: str | None
    annual_contract_value: float | None
    ownership: OwnershipView
    next_reassessment_on: date | None
    tags: list[str]
    source: str
    created_at: datetime
    updated_at: datetime
    engagement_count: int
    contact_count: int


@dataclass(frozen=True)
class VendorDetailView(VendorView):
    engagements: list[EngagementView] = field(default_factory=list)
    contacts: list[ContactView] = field(default_factory=list)
    duplicates: list[DuplicateMatch] = field(default_factory=list)
    # Flat lists carrying engagement_id, not nested under the engagement: the
    # rail and the tiering panel are separate screens and each wants its own
    # collection whole.
    stages: list[StageView] = field(default_factory=list)
    tierings: list[TieringView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VendorRef:
    """The lightweight vendor facts a sibling module needs (rule 4).

    Assets links a supplying third party and evidence names the vendor a document
    came from; neither should pay for ownership resolution or engagement loading.
    """

    id: uuid.UUID
    name: str
    tier: str | None
    lifecycle_status: str


@dataclass(frozen=True, slots=True)
class VendorFilters:
    search: str | None = None
    vendor_type: str | None = None
    statuses: tuple[str, ...] = ()
    tiers: tuple[str, ...] = ()
    classifications: tuple[str, ...] = ()
    business_units: tuple[str, ...] = ()
    owner: str | None = None  # membership_id, "me", or "unassigned"
    stores_pii: bool = False


@dataclass(frozen=True, slots=True)
class VendorInput:
    """The fields create/edit accept. The cached risk columns are derived, so the
    caller never supplies tier, residual score, grade or contract value."""

    name: str
    vendor_type: str = "vendor"
    industry: str | None = None
    website: str | None = None
    business_unit: str | None = None
    services_provided: str = ""
    stores_pii: bool = False
    data_location: str | None = None
    data_types_in_scope: tuple[str, ...] = ()
    data_classification: str | None = None
    tags: tuple[str, ...] = ()
    business_owner_membership_id: uuid.UUID | None = None
    security_owner_membership_id: uuid.UUID | None = None
    relationship_owner_membership_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class EngagementInput:
    name: str
    service_description: str = ""
    business_unit: str | None = None
    internal_owner_membership_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class ContactInput:
    name: str
    email: str | None = None
    phone: str | None = None
    contact_type: str = "commercial"


@dataclass(frozen=True, slots=True)
class ResolvedPolicy:
    """The tenant's tiering configuration, defaults already merged in."""

    weights: dict[str, float]
    thresholds: dict[str, float]
    skip_matrix: dict[str, tuple[str, ...]]
    reviewer_roles: dict[str, tuple[str, ...]]
    cadence_days: dict[str, int]
    is_customised: bool
    """False means every value here is a shipped default. The settings screen says
    so rather than presenting the defaults as choices somebody made."""


@dataclass(frozen=True, slots=True)
class TieringAnswers:
    """The five factor answers, plus an optional human override of the result."""

    data_sensitivity: int = 0
    business_criticality: int = 0
    system_access: int = 0
    regulatory_scope: int = 0
    fourth_party_reliance: int = 0
    override_tier: str | None = None
    override_justification: str | None = None

    def as_dict(self) -> dict[str, int]:
        return {key: getattr(self, key) for key in scoring.FACTOR_KEYS}


@dataclass(frozen=True, slots=True)
class TieringView:
    """One scored run with its arithmetic recomputed from the stored answers.

    The breakdown is derived on read from the answers and the run's own
    ``policy_snapshot``, never from today's policy — which is the whole reason
    that snapshot column exists.
    """

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    factors: list[scoring.TieringFactor]
    score: float
    computed_tier: str
    override_tier: str | None
    override_justification: str | None
    effective_tier: str
    thresholds: dict[str, float]
    points_to_higher_tier: float | None
    points_to_lower_tier: float | None
    assessed_by_name: str | None
    assessed_at: datetime | None


@dataclass(frozen=True, slots=True)
class StageView:
    """One row of the stage rail, with its exit checks already evaluated."""

    id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    stage: str
    label: str
    status: str
    is_gate: bool
    is_required: bool
    entered_at: datetime | None
    exited_at: datetime | None
    skipped_reason: str | None
    skipped_by_policy: str | None
    checks: list[lifecycle.ExitCheck]
    blockers: list[lifecycle.ExitCheck]
    pending: list[lifecycle.ExitCheck]
    """Checks whose answering module is not built yet. Never blocking, never a
    tick either — the distinction rule 7 draws between error and fail."""
    allowed_transitions: list[str]
    """Served so the client never reimplements the machine in TypeScript."""


# -- the review (section 3) ---------------------------------------------------

_QUESTIONNAIRE_DUE_DAYS: Final = 21
_PORTAL_TOKEN_DAYS: Final = 30
"""The link outlives the due date by a little, so a vendor who is late can still
answer rather than having to ask for a new link — which is friction that produces
an unanswered questionnaire, not a more secure one."""

_FINDING_SLA_DAYS: Final[dict[str, int]] = {
    "critical": 7,
    "high": 30,
    "medium": 90,
    "low": 180,
}

_TASK_PRIORITY: Final[dict[str, str]] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

_FINDING_SNAPSHOT: Final[tuple[str, ...]] = (
    "title",
    "severity",
    "status",
    "treatment",
    "is_blocking",
    "owner_membership_id",
    "task_id",
    "accepted_until",
)

_ASSESSMENT_GONE: Final = "This questionnaire no longer exists. It may have been deleted."
_FINDING_GONE: Final = "This finding no longer exists. It may have been closed and removed."


def _finding_severity(question: QuestionnaireQuestion) -> str:
    """How bad a ``no`` to this question is.

    Driven by what the question *is*, not by who answered it: a missing critical
    control is critical whoever the vendor is, and a nice-to-have is low however
    important the vendor.
    """
    if question.critical_control:
        return "critical"
    if question.weight >= _HIGH_WEIGHT:
        return "high"
    if question.weight >= _MEDIUM_WEIGHT:
        return "medium"
    return "low"


_HIGH_WEIGHT: Final = 2.0
_MEDIUM_WEIGHT: Final = 1.5


def _finding_title(question: QuestionnaireQuestion) -> str:
    """A title that names the gap, not the question.

    "Access control: MFA on privileged access" is something a reader can act on;
    the question text repeated back is something they have to translate first.
    """
    return f"{RISK_DOMAIN_LABELS[question.domain]}: {question.code}"


def _portal_url(token: str) -> str:
    base = get_settings().frontend_base_url.rstrip("/")
    return f"{base}/vendor-portal/{token}"


@dataclass(frozen=True, slots=True)
class IssuedQuestionnaire:
    """What issuing returns. ``portal_url`` contains the only copy of the token."""

    assessment_id: uuid.UUID
    contact_email: str
    question_count: int
    due_date: date | None
    portal_url: str


@dataclass(frozen=True, slots=True)
class ResponseView:
    id: uuid.UUID
    question_id: uuid.UUID
    question_code: str
    body: str
    domain: str
    domain_label: str
    scope_level: str
    answer_type: str
    weight: float
    critical_control: bool
    non_negotiable: bool
    evidence_required: bool
    framework_refs: list[str]
    answer: str | None
    implementation_notes: str | None
    na_justification: str | None
    evidence_id: uuid.UUID | None
    answered_at: datetime | None


@dataclass(frozen=True, slots=True)
class FindingView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    assessment_id: uuid.UUID | None
    question_id: uuid.UUID | None
    title: str
    detail: str
    finding_source: str
    severity: str
    status: str
    treatment: str
    is_blocking: bool
    sla_due: date | None
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    task_id: uuid.UUID | None
    accepted_until: date | None
    accepted_rationale: str | None
    closed_at: datetime | None
    promoted_risk_id: uuid.UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AssessmentView:
    id: uuid.UUID
    vendor_id: uuid.UUID
    engagement_id: uuid.UUID
    cycle: int
    kind: str
    review_format: str
    assessment_domain: str
    status: str
    decision: str
    due_date: date | None
    residual_score: float | None
    grade: str | None
    domain_scores: dict[str, Any]
    score_steps: list[Any]
    """The adjustments in the order they applied, including the ones that did not
    fire — the same shape the tiering panel reads."""
    scope: dict[str, Any]
    question_count: int
    answered_count: int
    unanswered_count: int
    missing_evidence_count: int
    submitted_at: datetime | None
    responses: list[ResponseView]
    findings: list[FindingView]
    portal_link_live: bool
    portal_link_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


# -- service ------------------------------------------------------------------


class VendorService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- cross-module resolution (rule 4) -------------------------------------

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    # -- helpers ---------------------------------------------------------------

    async def _load(
        self, session: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> Vendor:
        # populate_existing forces a fresh row so a mutating method that re-renders
        # through here does not read an expired server-computed column.
        vendor = await session.get(Vendor, vendor_id, populate_existing=True)
        if vendor is None or vendor.tenant_id != tenant_id:
            raise NotFound(_VENDOR_GONE, detail=f"vendor {vendor_id}")
        return vendor

    async def _load_engagement(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID
    ) -> VendorEngagement:
        engagement = await session.get(VendorEngagement, engagement_id, populate_existing=True)
        if engagement is None or engagement.tenant_id != tenant_id:
            raise NotFound(_ENGAGEMENT_GONE, detail=f"vendor engagement {engagement_id}")
        return engagement

    @staticmethod
    def _clean(value: str | None) -> str | None:
        cleaned = (value or "").strip()
        return cleaned or None

    @staticmethod
    def _require_name(name: str, *, what: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise InvalidInput(
                f"Give this {what} a name before saving it.",
                detail=f"a {what} needs a name",
            )
        return cleaned

    @staticmethod
    def _check_vocabulary(value: str | None, allowed: tuple[str, ...], *, field_name: str) -> None:
        """Reject an unknown value here so the caller gets 422 and a readable line.

        The database CHECK is the wall and would raise too, but as an opaque
        integrity error with the constraint name in it.
        """
        if value is not None and value not in allowed:
            raise InvalidInput(
                f"That {field_name.replace('_', ' ')} is not one we recognise. "
                f"Pick one of: {', '.join(allowed)}.",
                detail=f"{field_name}={value!r} is not in {allowed}",
            )

    def _assign(self, vendor: Vendor, data: VendorInput) -> None:
        self._check_vocabulary(data.vendor_type, VENDOR_TYPES, field_name="vendor_type")
        self._check_vocabulary(
            data.data_classification, DATA_CLASSIFICATIONS, field_name="data_classification"
        )
        vendor.name = self._require_name(data.name, what="vendor")
        vendor.vendor_type = data.vendor_type
        vendor.industry = self._clean(data.industry)
        vendor.website = self._clean(data.website)
        vendor.business_unit = self._clean(data.business_unit)
        vendor.services_provided = data.services_provided.strip()
        vendor.stores_pii = data.stores_pii
        vendor.data_location = self._clean(data.data_location)
        vendor.data_types_in_scope = list(data.data_types_in_scope)
        vendor.data_classification = data.data_classification
        vendor.tags = list(data.tags)
        vendor.business_owner_membership_id = data.business_owner_membership_id
        vendor.security_owner_membership_id = data.security_owner_membership_id
        vendor.relationship_owner_membership_id = data.relationship_owner_membership_id

    async def _engagements_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, *vendor_ids: uuid.UUID
    ) -> dict[uuid.UUID, list[VendorEngagement]]:
        if not vendor_ids:
            return {}
        stmt = (
            select(VendorEngagement)
            .where(VendorEngagement.tenant_id == tenant_id)
            .where(VendorEngagement.vendor_id.in_(list(vendor_ids)))
            .order_by(VendorEngagement.created_at)
        )
        grouped: dict[uuid.UUID, list[VendorEngagement]] = {}
        for row in (await session.execute(stmt)).scalars():
            grouped.setdefault(row.vendor_id, []).append(row)
        return grouped

    async def _contacts_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, *vendor_ids: uuid.UUID
    ) -> dict[uuid.UUID, list[VendorContact]]:
        if not vendor_ids:
            return {}
        stmt = (
            select(VendorContact)
            .where(VendorContact.tenant_id == tenant_id)
            .where(VendorContact.vendor_id.in_(list(vendor_ids)))
            .order_by(VendorContact.name)
        )
        grouped: dict[uuid.UUID, list[VendorContact]] = {}
        for row in (await session.execute(stmt)).scalars():
            grouped.setdefault(row.vendor_id, []).append(row)
        return grouped

    async def _counts(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
        """Engagement and contact counts per vendor, two grouped counts not an N+1."""

        async def tally(
            model: type[VendorEngagement] | type[VendorContact],
        ) -> dict[uuid.UUID, int]:
            stmt = (
                select(model.vendor_id, func.count())
                .where(model.tenant_id == tenant_id)
                .group_by(model.vendor_id)
            )
            return {row[0]: row[1] for row in (await session.execute(stmt)).all()}

        return await tally(VendorEngagement), await tally(VendorContact)

    # -- the cached read-model columns (V10) -----------------------------------

    @staticmethod
    def _worst_tier(engagements: list[VendorEngagement]) -> str | None:
        tiers = [e.tier for e in engagements if e.tier in TIER_RANK]
        if not tiers:
            return None
        return min(tiers, key=lambda t: TIER_RANK[str(t)])

    async def _recache(self, session: AsyncSession, tenant_id: uuid.UUID, vendor: Vendor) -> None:
        """Refresh the vendor's cached worst-engagement columns.

        The only writer of ``vendor.tier``. Residual score, grade and contract
        value stay untouched here: the engines that produce them are sections 3
        and 4, and writing a placeholder now would make an unscored vendor look
        scored.
        """
        engagements = (await self._engagements_of(session, tenant_id, vendor.id)).get(vendor.id, [])
        vendor.tier = self._worst_tier(engagements)

    # -- views -----------------------------------------------------------------

    def _ownership(self, vendor: Vendor, names: dict[uuid.UUID, str]) -> OwnershipView:
        def named(member_id: uuid.UUID | None) -> str | None:
            return names.get(member_id) if member_id else None

        return OwnershipView(
            business_owner_membership_id=vendor.business_owner_membership_id,
            business_owner_name=named(vendor.business_owner_membership_id),
            security_owner_membership_id=vendor.security_owner_membership_id,
            security_owner_name=named(vendor.security_owner_membership_id),
            relationship_owner_membership_id=vendor.relationship_owner_membership_id,
            relationship_owner_name=named(vendor.relationship_owner_membership_id),
        )

    def _to_view(
        self,
        vendor: Vendor,
        names: dict[uuid.UUID, str],
        engagement_count: int,
        contact_count: int,
    ) -> VendorView:
        return VendorView(
            id=vendor.id,
            name=vendor.name,
            vendor_type=vendor.vendor_type,
            industry=vendor.industry,
            website=vendor.website,
            business_unit=vendor.business_unit,
            services_provided=vendor.services_provided,
            stores_pii=vendor.stores_pii,
            data_location=vendor.data_location,
            data_types_in_scope=list(vendor.data_types_in_scope or []),
            data_classification=vendor.data_classification,
            lifecycle_status=vendor.lifecycle_status,
            tier=vendor.tier,
            current_residual_score=vendor.current_residual_score,
            current_grade=vendor.current_grade,
            annual_contract_value=vendor.annual_contract_value,
            ownership=self._ownership(vendor, names),
            next_reassessment_on=vendor.next_reassessment_on,
            tags=list(vendor.tags or []),
            source=vendor.source,
            created_at=vendor.created_at,
            updated_at=vendor.updated_at,
            engagement_count=engagement_count,
            contact_count=contact_count,
        )

    @staticmethod
    def _engagement_view(
        engagement: VendorEngagement, names: dict[uuid.UUID, str]
    ) -> EngagementView:
        owner = engagement.internal_owner_membership_id
        return EngagementView(
            id=engagement.id,
            vendor_id=engagement.vendor_id,
            name=engagement.name,
            service_description=engagement.service_description,
            business_unit=engagement.business_unit,
            internal_owner_membership_id=owner,
            internal_owner_name=names.get(owner) if owner else None,
            tier=engagement.tier,
            status=engagement.status,
            start_date=engagement.start_date,
            end_date=engagement.end_date,
            created_at=engagement.created_at,
            updated_at=engagement.updated_at,
        )

    @staticmethod
    def _contact_view(contact: VendorContact) -> ContactView:
        return ContactView(
            id=contact.id,
            vendor_id=contact.vendor_id,
            name=contact.name,
            email=contact.email,
            phone=contact.phone,
            contact_type=contact.contact_type,
        )

    # -- duplicate detection (ER ¶90) — warns, never blocks --------------------

    async def find_duplicates(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        name: str,
        website: str | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> list[DuplicateMatch]:
        """Vendors that look like this one. Called on save and by the create form.

        Deliberately not a unique constraint: two genuinely different subsidiaries
        share a trading name, and a hard constraint would refuse a legitimate
        record rather than let a person judge.
        """
        target_name = _fingerprint(name)
        target_domain = _domain(website)
        if not target_name and not target_domain:
            return []

        stmt = select(Vendor).where(Vendor.tenant_id == tenant_id)
        if exclude_id is not None:
            stmt = stmt.where(Vendor.id != exclude_id)
        matches: list[DuplicateMatch] = []
        for other in (await session.execute(stmt)).scalars():
            if target_name and _fingerprint(other.name) == target_name:
                matches.append(DuplicateMatch(id=other.id, name=other.name, reason="same_name"))
            elif target_domain and _domain(other.website) == target_domain:
                matches.append(DuplicateMatch(id=other.id, name=other.name, reason="same_website"))
        return matches

    # -- reads -----------------------------------------------------------------

    async def list_vendors(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        filters: VendorFilters,
        page: int = 1,
        page_size: int = 25,
        caller_membership_id: uuid.UUID | None = None,
    ) -> tuple[list[VendorView], int]:
        stmt = select(Vendor).where(Vendor.tenant_id == tenant_id)
        if filters.vendor_type and filters.vendor_type != "all":
            stmt = stmt.where(Vendor.vendor_type == filters.vendor_type)
        if filters.statuses:
            stmt = stmt.where(Vendor.lifecycle_status.in_(list(filters.statuses)))
        if filters.tiers:
            stmt = stmt.where(Vendor.tier.in_(list(filters.tiers)))
        if filters.classifications:
            stmt = stmt.where(Vendor.data_classification.in_(list(filters.classifications)))
        if filters.business_units:
            stmt = stmt.where(Vendor.business_unit.in_(list(filters.business_units)))
        if filters.stores_pii:
            stmt = stmt.where(Vendor.stores_pii.is_(True))
        if filters.owner == "unassigned":
            stmt = stmt.where(Vendor.business_owner_membership_id.is_(None))
        elif filters.owner == "me" and caller_membership_id is not None:
            stmt = stmt.where(Vendor.business_owner_membership_id == caller_membership_id)
        elif filters.owner:
            stmt = stmt.where(Vendor.business_owner_membership_id == uuid.UUID(filters.owner))
        if filters.search:
            like = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Vendor.name).like(like),
                    func.lower(func.coalesce(Vendor.website, "")).like(like),
                    func.lower(func.coalesce(Vendor.industry, "")).like(like),
                    func.lower(func.coalesce(Vendor.business_unit, "")).like(like),
                    func.lower(Vendor.services_provided).like(like),
                )
            )

        vendors = list((await session.execute(stmt)).scalars())
        names = await self._member_names(session, tenant_id)
        engagement_counts, contact_counts = await self._counts(session, tenant_id)
        views = [
            self._to_view(v, names, engagement_counts.get(v.id, 0), contact_counts.get(v.id, 0))
            for v in vendors
        ]
        views.sort(key=self._register_sort_key)
        total = len(views)
        start = (page - 1) * page_size
        return views[start : start + page_size], total

    @staticmethod
    def _register_sort_key(v: VendorView) -> tuple[int, int, str]:
        """Worst tier first, then unowned, then alphabetical.

        Unowned sorts up because a vendor nobody owns is the one nobody will
        notice, which is exactly the row a register exists to surface.
        """
        tier_rank = TIER_RANK.get(v.tier or "", 9)
        unowned = 0 if v.ownership.business_owner_membership_id is None else 1
        return tier_rank, unowned, v.name.lower()

    async def get_vendor(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        names = await self._member_names(session, tenant_id)
        engagements = (await self._engagements_of(session, tenant_id, vendor.id)).get(vendor.id, [])
        contacts = (await self._contacts_of(session, tenant_id, vendor.id)).get(vendor.id, [])
        base = self._to_view(vendor, names, len(engagements), len(contacts))
        stages: list[StageView] = []
        tierings: list[TieringView] = []
        for engagement in engagements:
            cycle = await self._current_cycle(session, tenant_id, engagement.id)
            stages.extend(await self._stage_views(session, tenant_id, vendor, engagement, cycle))
            latest = await self._latest_tiering(session, tenant_id, engagement.id, cycle)
            if latest is not None:
                tierings.append(self._tiering_view(latest, names))
        return VendorDetailView(
            **{f: getattr(base, f) for f in base.__dataclass_fields__},
            engagements=[self._engagement_view(e, names) for e in engagements],
            contacts=[self._contact_view(c) for c in contacts],
            duplicates=await self.find_duplicates(
                session,
                tenant_id=tenant_id,
                name=vendor.name,
                website=vendor.website,
                exclude_id=vendor.id,
            ),
            stages=stages,
            tierings=tierings,
        )

    @staticmethod
    def _tiering_view(row: VendorTieringAssessment, names: dict[uuid.UUID, str]) -> TieringView:
        """Recompute the arithmetic from the answers and the run's own snapshot.

        Deliberately not from today's policy: an assessment has to keep meaning
        what it meant when it was made, or "why is this vendor critical" becomes
        unanswerable the moment somebody retunes the weights.
        """
        snapshot = row.policy_snapshot or {}
        breakdown = scoring.compute_tier(
            {key: getattr(row, key) for key in scoring.FACTOR_KEYS},
            weights=snapshot.get("weights"),
            thresholds=snapshot.get("thresholds"),
        )
        owner = row.assessed_by_membership_id
        return TieringView(
            id=row.id,
            engagement_id=row.engagement_id,
            cycle=row.cycle,
            factors=list(breakdown.factors),
            score=row.inherent_score,
            computed_tier=row.computed_tier,
            override_tier=row.override_tier,
            override_justification=row.override_justification,
            effective_tier=row.override_tier or row.computed_tier,
            thresholds=breakdown.thresholds,
            points_to_higher_tier=breakdown.points_to_higher_tier,
            points_to_lower_tier=breakdown.points_to_lower_tier,
            assessed_by_name=names.get(owner) if owner else None,
            assessed_at=row.assessed_at,
        )

    async def get_ref(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> VendorRef:
        """The cross-module read (rule 4). Siblings call this, never ``get_vendor``."""
        vendor = await self._load(session, tenant_id, vendor_id)
        return VendorRef(
            id=vendor.id,
            name=vendor.name,
            tier=vendor.tier,
            lifecycle_status=vendor.lifecycle_status,
        )

    async def facets(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
        """The register's filter vocabularies, served rather than hardcoded."""
        units = (
            await session.execute(
                select(Vendor.business_unit)
                .where(Vendor.tenant_id == tenant_id)
                .where(Vendor.business_unit.is_not(None))
                .distinct()
                .order_by(Vendor.business_unit)
            )
        ).scalars()
        policy = await self._resolved_policy(session, tenant_id)
        return {
            "vendor_types": list(VENDOR_TYPES),
            "statuses": list(LIFECYCLE_STATUSES),
            "tiers": list(TIERS),
            "classifications": list(DATA_CLASSIFICATIONS),
            "contact_types": list(CONTACT_TYPES),
            "business_units": [u for u in units if u],
            # The lifecycle vocabulary, served rather than reimplemented in
            # TypeScript — which is how the two drift and the interface offers a
            # move the API then refuses.
            "stages": [
                {
                    "stage": stage,
                    "label": lifecycle.STAGE_LABELS[stage],
                    "is_gate": stage in lifecycle.GATES,
                    "is_required": stage in lifecycle.REQUIRED_STAGES,
                }
                for stage in lifecycle.STAGES
            ],
            "skip_matrix_by_tier": {
                tier: sorted(lifecycle.skips_for(tier, policy.skip_matrix)) for tier in TIERS
            },
            "tiering_factors": [
                {
                    "key": key,
                    "label": scoring.FACTOR_LABELS[key],
                    "weight": policy.weights.get(key, 0.0),
                    "scale_max": scoring.FACTOR_SCALE_MAX,
                }
                for key in scoring.FACTOR_KEYS
            ],
            "tier_thresholds": policy.thresholds,
            "policy_is_customised": policy.is_customised,
        }

    # -- writes ----------------------------------------------------------------

    async def create_vendor(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        data: VendorInput,
        engagement: EngagementInput | None = None,
    ) -> VendorDetailView:
        """Create the vendor and its first engagement in one transaction (V10).

        ``engagement`` names the first use explicitly; omitting it creates the
        implicit default, which is what keeps a small workspace from ever having
        to learn the word "engagement".
        """
        vendor = Vendor(id=uuid7(), tenant_id=tenant_id, lifecycle_status="requested")
        self._assign(vendor, data)
        session.add(vendor)
        await session.flush([vendor])

        first = engagement or EngagementInput(
            name=DEFAULT_ENGAGEMENT_NAME,
            service_description=vendor.services_provided,
            business_unit=vendor.business_unit,
        )
        await self._add_engagement(session, tenant_id, vendor, first, actor, audit=False)

        await self._audit.record(
            session,
            action="create",
            object_type="vendor",
            object_id=vendor.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after=AuditService.snapshot(vendor, fields=_SNAPSHOT),
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def update_vendor(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: VendorInput,
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        before = AuditService.snapshot(vendor, fields=_SNAPSHOT)
        self._assign(vendor, data)
        after = AuditService.snapshot(vendor, fields=_SNAPSHOT)
        if before != after:
            await self._audit.record(
                session,
                action="update",
                object_type="vendor",
                object_id=vendor.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def _add_engagement(  # noqa: PLR0913
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor: Vendor,
        data: EngagementInput,
        actor: Actor,
        *,
        audit: bool,
    ) -> VendorEngagement:
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise InvalidInput(
                "The end date falls before the start date. Check the dates and try again.",
                detail=f"end_date {data.end_date} precedes start_date {data.start_date}",
            )
        engagement = VendorEngagement(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            name=self._require_name(data.name, what="engagement"),
            service_description=data.service_description.strip(),
            business_unit=self._clean(data.business_unit),
            internal_owner_membership_id=data.internal_owner_membership_id,
            status=vendor.lifecycle_status,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        session.add(engagement)
        await session.flush([engagement])
        if audit:
            await self._audit.record(
                session,
                action="create",
                object_type="vendor_engagement",
                object_id=engagement.id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after=AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT),
            )
        return engagement

    async def add_engagement(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: EngagementInput,
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        await self._add_engagement(session, tenant_id, vendor, data, actor, audit=True)
        await self._recache(session, tenant_id, vendor)
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor_id)

    async def update_engagement(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        data: EngagementInput,
    ) -> VendorDetailView:
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            # The path says which vendor this engagement belongs to. Disagreeing
            # with the record is a stale link or a guess, not an edit.
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} is not on vendor {vendor_id}"
            )
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise InvalidInput(
                "The end date falls before the start date. Check the dates and try again.",
                detail=f"end_date {data.end_date} precedes start_date {data.start_date}",
            )
        before = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        engagement.name = self._require_name(data.name, what="engagement")
        engagement.service_description = data.service_description.strip()
        engagement.business_unit = self._clean(data.business_unit)
        engagement.internal_owner_membership_id = data.internal_owner_membership_id
        engagement.start_date = data.start_date
        engagement.end_date = data.end_date
        after = AuditService.snapshot(engagement, fields=_ENGAGEMENT_SNAPSHOT)
        if before != after:
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_engagement",
                object_id=engagement.id,
                actor=actor,
                tenant_id=tenant_id,
                before=before,
                after=after,
            )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=engagement.vendor_id)

    async def add_contact(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        data: ContactInput,
    ) -> VendorDetailView:
        vendor = await self._load(session, tenant_id, vendor_id)
        self._check_vocabulary(data.contact_type, CONTACT_TYPES, field_name="contact_type")
        email = self._clean(data.email)
        if data.contact_type == "portal" and not email:
            raise InvalidInput(
                "A portal contact needs an email address — it is who the "
                "questionnaire link is sent to.",
                detail="portal contact without an email",
            )
        contact = VendorContact(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            name=self._require_name(data.name, what="contact"),
            email=email,
            phone=self._clean(data.phone),
            contact_type=data.contact_type,
        )
        session.add(contact)
        await session.flush([contact])
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_contact",
            object_id=contact.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={"name": contact.name, "contact_type": contact.contact_type},
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor_id)

    # -- tiering and the lifecycle (section 2) ---------------------------------

    async def _policy(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> VendorTieringPolicy | None:
        return (
            await session.execute(
                select(VendorTieringPolicy).where(VendorTieringPolicy.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()

    async def _resolved_policy(self, session: AsyncSession, tenant_id: uuid.UUID) -> ResolvedPolicy:
        """The tenant's tuning, falling back to the shipped defaults field by field.

        Field by field, not row or nothing: a tenant that overrode only the cadence
        should not silently lose the default weights with it.
        """
        row = await self._policy(session, tenant_id)
        skip_matrix = {
            tier: tuple(stages)
            for tier, stages in (row.stage_skip_matrix_by_tier if row else {}).items()
        }
        reviewers = {
            tier: tuple(roles)
            for tier, roles in (row.required_reviewer_roles_by_tier if row else {}).items()
        }
        return ResolvedPolicy(
            weights={**scoring.DEFAULT_WEIGHTS, **((row.factor_weights if row else None) or {})},
            thresholds={
                **scoring.DEFAULT_THRESHOLDS,
                **((row.tier_thresholds if row else None) or {}),
            },
            skip_matrix={**lifecycle.DEFAULT_SKIP_MATRIX, **skip_matrix},
            reviewer_roles={**lifecycle.DEFAULT_REVIEWER_ROLES, **reviewers},
            cadence_days={
                **lifecycle.DEFAULT_CADENCE_DAYS,
                **((row.cadence_days_by_tier if row else None) or {}),
            },
            is_customised=row is not None,
        )

    async def _stages_for(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> list[VendorStage]:
        stmt = (
            select(VendorStage)
            .where(VendorStage.tenant_id == tenant_id)
            .where(VendorStage.engagement_id == engagement_id)
            .where(VendorStage.cycle == cycle)
        )
        rows = list((await session.execute(stmt)).scalars())
        order = {stage: index for index, stage in enumerate(lifecycle.STAGES)}
        rows.sort(key=lambda row: order[row.stage])
        return rows

    async def _current_cycle(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID
    ) -> int:
        highest = (
            await session.execute(
                select(func.max(VendorStage.cycle))
                .where(VendorStage.tenant_id == tenant_id)
                .where(VendorStage.engagement_id == engagement_id)
            )
        ).scalar_one_or_none()
        return int(highest or 1)

    async def _latest_tiering(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> VendorTieringAssessment | None:
        stmt = (
            select(VendorTieringAssessment)
            .where(VendorTieringAssessment.tenant_id == tenant_id)
            .where(VendorTieringAssessment.engagement_id == engagement_id)
            .where(VendorTieringAssessment.cycle == cycle)
            .order_by(VendorTieringAssessment.created_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def _latest_assessment(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> VendorAssessment | None:
        return (
            await session.execute(
                select(VendorAssessment)
                .where(VendorAssessment.tenant_id == tenant_id)
                .where(VendorAssessment.engagement_id == engagement_id)
                .where(VendorAssessment.cycle == cycle)
                .order_by(VendorAssessment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _facts(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor: Vendor,
        engagement: VendorEngagement,
        stage: VendorStage,
        policy: ResolvedPolicy,
    ) -> lifecycle.StageFacts:
        tiering = await self._latest_tiering(session, tenant_id, engagement.id, stage.cycle)
        tier = engagement.tier
        # Section 3 built the assessment and finding tables, so the checks that
        # reported pending are answerable now. Nothing in lifecycle.py changed:
        # the rules were always written, and this is the collector catching up.
        assessment = await self._latest_assessment(session, tenant_id, engagement.id, stage.cycle)
        answers = (
            await self.answers_with_questions(
                session, tenant_id=tenant_id, assessment_id=assessment.id
            )
            if assessment
            else []
        )
        return lifecycle.StageFacts(
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            tier=tier,
            business_owner_membership_id=vendor.business_owner_membership_id,
            data_classification=vendor.data_classification,
            tiering_assessment_id=tiering.id if tiering else None,
            stage_entered_at=stage.entered_at,
            next_cycle_opened=stage.cycle
            < await self._current_cycle(session, tenant_id, engagement.id),
            required_reviewer_roles=policy.reviewer_roles.get(tier or "", ()),
            assessments_available=True,
            selected_bank_count=1 if assessment else 0,
            unanswered_question_count=sum(1 for r, _ in answers if not r.answer),
            missing_evidence_count=sum(
                1
                for r, q in answers
                if q.evidence_required and r.answer == "yes" and not r.evidence_id
            ),
            residual_score=assessment.residual_score if assessment else None,
            findings_available=True,
            open_critical_findings=await self.open_critical_count(
                session, tenant_id=tenant_id, vendor_id=vendor.id
            ),
            # vendor_team_roster is a section-4 table. Until it exists nobody is
            # rostered, so every required role reports as missing — which is true
            # and visible, rather than quietly passing.
            assigned_reviewer_roles=(),
        )

    async def _stage_views(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor: Vendor,
        engagement: VendorEngagement,
        cycle: int,
    ) -> list[StageView]:
        policy = await self._resolved_policy(session, tenant_id)
        skippable = lifecycle.skips_for(engagement.tier, policy.skip_matrix)
        rows = await self._stages_for(session, tenant_id, engagement.id, cycle)
        order = {stage: index for index, stage in enumerate(lifecycle.STAGES)}
        views: list[StageView] = []
        for row in rows:
            checks = lifecycle.evaluate_exit(
                row.stage, await self._facts(session, tenant_id, vendor, engagement, row, policy)
            )
            state = lifecycle.StageState(
                stage=row.stage, status=row.status, is_gate=row.is_gate, is_required=row.is_required
            )
            views.append(
                StageView(
                    id=row.id,
                    engagement_id=row.engagement_id,
                    cycle=row.cycle,
                    stage=row.stage,
                    label=lifecycle.STAGE_LABELS[row.stage],
                    status=row.status,
                    is_gate=row.is_gate,
                    is_required=row.is_required,
                    entered_at=row.entered_at,
                    exited_at=row.exited_at,
                    skipped_reason=row.skipped_reason,
                    skipped_by_policy=row.skipped_by_policy,
                    checks=list(checks),
                    blockers=list(lifecycle.blockers(checks)),
                    pending=list(lifecycle.pending(checks)),
                    allowed_transitions=list(
                        lifecycle.allowed_transitions(
                            state,
                            checks,
                            skippable=skippable,
                            has_earlier_stage=order[row.stage] > 0,
                        )
                    ),
                )
            )
        return views

    async def _write_transition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        stage: VendorStage,
        actor: Actor,
        action: str,
        *,
        to_stage: str | None,
        reason: str | None,
    ) -> None:
        """Both records, one transaction: the columnar row and the audit row.

        Two histories on purpose. ``vendor_transitions`` is the domain view an
        operator reads down; ``audit_log`` is the platform trail an auditor reads
        across. Writing only one of them makes the other lie by omission.
        """
        now = datetime.now(UTC)
        session.add(
            VendorTransition(
                id=uuid7(),
                tenant_id=tenant_id,
                vendor_id=stage.vendor_id,
                engagement_id=stage.engagement_id,
                stage_id=stage.id,
                cycle=stage.cycle,
                action=action,
                from_stage=stage.stage,
                to_stage=to_stage,
                reason=reason,
                actor_membership_id=actor.id if isinstance(actor, Membership) else None,
                occurred_at=now,
            )
        )
        await session.flush()
        await self._audit.record(
            session,
            action="transition",
            object_type="vendor_stage",
            object_id=stage.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"stage": stage.stage, "status": stage.status},
            after={"action": action, "to_stage": to_stage, "reason": reason},
        )

    async def materialise_cycle(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        engagement: VendorEngagement,
        cycle: int,
        policy: ResolvedPolicy,
    ) -> list[VendorStage]:
        """Write the twelve rows for one cycle, this tier's skips already marked.

        Idempotent: an existing cycle is re-planned in place rather than
        duplicated, so re-running tiering after a retier moves the skips instead
        of colliding with the unique constraint.
        """
        existing = {
            row.stage: row
            for row in await self._stages_for(session, tenant_id, engagement.id, cycle)
        }
        rows: list[VendorStage] = []
        for planned in lifecycle.plan_cycle(engagement.tier, policy.skip_matrix):
            row = existing.get(planned.stage)
            if row is None:
                row = VendorStage(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    vendor_id=engagement.vendor_id,
                    engagement_id=engagement.id,
                    cycle=cycle,
                    stage=planned.stage,
                    status=planned.status,
                    is_gate=planned.is_gate,
                    is_required=planned.is_required,
                    skipped_by_policy=planned.skipped_by_policy,
                )
                session.add(row)
            elif row.status in {"not_started", "skipped"}:
                # Never re-plan work already done or under way: a retier changes
                # what is still ahead, not what has already been decided.
                row.status = planned.status
                row.skipped_by_policy = planned.skipped_by_policy
            rows.append(row)
        await session.flush()
        return rows

    async def tier_engagement(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        answers: TieringAnswers,
    ) -> VendorDetailView:
        """Score the five factors, set the tier, and lay out the cycle it implies.

        This is the method spec paragraph 82 is about: the tier is computed here
        and the *work* changes in the same transaction, because a tier that does
        not change the workload has added a dropdown rather than a control.
        """
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE,
                detail=f"engagement {engagement_id} is not on vendor {vendor_id}",
            )
        vendor = await self._load(session, tenant_id, vendor_id)
        if answers.override_tier and not (answers.override_justification or "").strip():
            raise InvalidInput(
                "Say why you are overriding the computed tier. The justification is "
                "what makes the override defensible to an auditor.",
                detail="override_tier without override_justification",
            )
        self._check_vocabulary(answers.override_tier, TIERS, field_name="override_tier")

        policy = await self._resolved_policy(session, tenant_id)
        breakdown = scoring.compute_tier(
            answers.as_dict(), weights=policy.weights, thresholds=policy.thresholds
        )
        cycle = await self._current_cycle(session, tenant_id, engagement.id)
        assessment = VendorTieringAssessment(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=engagement.id,
            cycle=cycle,
            data_sensitivity=answers.data_sensitivity,
            business_criticality=answers.business_criticality,
            system_access=answers.system_access,
            regulatory_scope=answers.regulatory_scope,
            fourth_party_reliance=answers.fourth_party_reliance,
            inherent_score=breakdown.score,
            computed_tier=breakdown.tier,
            override_tier=answers.override_tier,
            override_justification=(answers.override_justification or "").strip() or None,
            # Frozen with the row, so a later retune of the policy cannot rewrite
            # what this assessment meant when it was made.
            policy_snapshot={"weights": policy.weights, "thresholds": policy.thresholds},
            assessed_by_membership_id=actor.id if isinstance(actor, Membership) else None,
            assessed_at=datetime.now(UTC),
        )
        session.add(assessment)
        await session.flush([assessment])

        engagement.tier = answers.override_tier or breakdown.tier
        await self.materialise_cycle(session, tenant_id, engagement, cycle, policy)
        await self._recache(session, tenant_id, vendor)
        self._schedule_reassessment(vendor, engagement.tier, policy)

        await self._audit.record(
            session,
            action="create",
            object_type="vendor_tiering_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "engagement_id": str(engagement.id),
                "inherent_score": breakdown.score,
                "computed_tier": breakdown.tier,
                "override_tier": answers.override_tier,
            },
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    @staticmethod
    def _schedule_reassessment(vendor: Vendor, tier: str | None, policy: ResolvedPolicy) -> None:
        """Set the next review date from the cadence, not from today's completion.

        Anchored to the previous due date where one exists, so a review done late
        does not push the next one late. Reviews that drift a little further out
        every cycle is the failure this rule exists to prevent (ER 101).
        """
        days = policy.cadence_days.get(tier or "", 0)
        if not days:
            return
        anchor = vendor.next_reassessment_on or datetime.now(UTC).date()
        vendor.next_reassessment_on = anchor + timedelta(days=int(days))

    async def _load_stage(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
    ) -> VendorStage:
        stage = await session.get(VendorStage, stage_id, populate_existing=True)
        if stage is None or stage.tenant_id != tenant_id or stage.vendor_id != vendor_id:
            raise NotFound(_STAGE_GONE, detail=f"vendor stage {stage_id} on vendor {vendor_id}")
        return stage

    async def advance_stage(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
        note: str | None = None,
    ) -> VendorDetailView:
        """Complete this stage and enter the next one that is not skipped."""
        stage = await self._load_stage(session, tenant_id, vendor_id, stage_id)
        engagement = await self._load_engagement(session, tenant_id, stage.engagement_id)
        vendor = await self._load(session, tenant_id, vendor_id)
        policy = await self._resolved_policy(session, tenant_id)

        checks = lifecycle.evaluate_exit(
            stage.stage, await self._facts(session, tenant_id, vendor, engagement, stage, policy)
        )
        outstanding = lifecycle.blockers(checks)
        if outstanding:
            raise Conflict(
                "This stage still has work outstanding. Clear the blockers listed on "
                "it and try again.",
                detail=f"{stage.stage} blocked by {[c.code for c in outstanding]}",
            )
        if stage.stage == lifecycle.TERMINAL_STAGE:
            raise Conflict(
                "Offboarding is the end of the lifecycle. There is nothing after it.",
                detail="advance from the terminal stage",
            )

        now = datetime.now(UTC)
        stage.status = "complete"
        stage.exited_at = now
        rows = await self._stages_for(session, tenant_id, engagement.id, stage.cycle)
        # Walk over the skipped rows, so a low-tier vendor goes from tiering to
        # contracting in one move and the proportionality is visible.
        target = lifecycle.next_actionable([(r.stage, r.status) for r in rows], stage.stage)
        if target is not None:
            nxt = next(r for r in rows if r.stage == target)
            nxt.status = "in_progress"
            nxt.entered_at = now
        await self._write_transition(
            session, tenant_id, stage, actor, "advance", to_stage=target, reason=note
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def send_back(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
        to_stage: str,
        reason: str,
    ) -> VendorDetailView:
        """Return the engagement to an earlier stage, resetting everything after it.

        Downstream work is invalidated **by design**. Combined with the
        gate-freshness rule, a previously granted approval stops counting without
        the append-only approval row ever being touched.
        """
        stage = await self._load_stage(session, tenant_id, vendor_id, stage_id)
        vendor = await self._load(session, tenant_id, vendor_id)
        if not reason.strip():
            raise InvalidInput(
                "Say why you are sending this back. The reason is what the owner "
                "sees when they pick it up.",
                detail="send_back without a reason",
            )
        order = {name: index for index, name in enumerate(lifecycle.STAGES)}
        if to_stage not in order:
            raise InvalidInput(
                "That is not a stage in the lifecycle.", detail=f"unknown stage {to_stage!r}"
            )
        if order[to_stage] >= order[stage.stage]:
            raise Conflict(
                "A send-back only goes backwards. To move forward, clear this "
                "stage's blockers and advance.",
                detail=f"send_back from {stage.stage} to {to_stage}",
            )

        now = datetime.now(UTC)
        rows = await self._stages_for(session, tenant_id, stage.engagement_id, stage.cycle)
        for row in rows:
            if order[row.stage] < order[to_stage] or row.status == "skipped":
                continue
            row.status = "in_progress" if row.stage == to_stage else "not_started"
            row.entered_at = now if row.stage == to_stage else None
            row.exited_at = None
        await self._write_transition(
            session, tenant_id, stage, actor, "send_back", to_stage=to_stage, reason=reason.strip()
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    async def skip_stage(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        stage_id: uuid.UUID,
        reason: str,
    ) -> VendorDetailView:
        """Mark a stage skipped, if this tier's policy permits it.

        A gate is refused here and refused again by a database CHECK. Two layers
        because spec paragraph 82's "approval gates are never skipped" is a
        control statement, and a control enforced only in application code is a
        control one bug away from not existing.
        """
        stage = await self._load_stage(session, tenant_id, vendor_id, stage_id)
        engagement = await self._load_engagement(session, tenant_id, stage.engagement_id)
        vendor = await self._load(session, tenant_id, vendor_id)
        if not reason.strip():
            raise InvalidInput(
                "Say why this stage is being skipped. A skip with no reason is "
                "indistinguishable from an oversight.",
                detail="skip without a reason",
            )
        if stage.is_gate:
            raise Conflict(
                "An approval gate can never be skipped, whatever the tier.",
                detail=f"skip refused on gate {stage.stage}",
            )
        if stage.is_required:
            raise Conflict(
                f"{lifecycle.STAGE_LABELS[stage.stage]} is required for every vendor "
                "and cannot be skipped.",
                detail=f"skip refused on required stage {stage.stage}",
            )
        policy = await self._resolved_policy(session, tenant_id)
        if stage.stage not in lifecycle.skips_for(engagement.tier, policy.skip_matrix):
            raise Conflict(
                f"A {engagement.tier or 'vendor'}-tier engagement does not skip "
                f"{lifecycle.STAGE_LABELS[stage.stage].lower()}. Retier it, or clear "
                "the stage.",
                detail=f"{stage.stage} not skippable at tier {engagement.tier}",
            )

        stage.status = "skipped"
        stage.skipped_reason = reason.strip()
        stage.skipped_by_membership_id = actor.id if isinstance(actor, Membership) else None
        stage.exited_at = datetime.now(UTC)
        await self._write_transition(
            session, tenant_id, stage, actor, "skip", to_stage=None, reason=reason.strip()
        )
        await session.flush()
        return await self.get_vendor(session, tenant_id=tenant_id, vendor_id=vendor.id)

    # -- the questionnaire (section 3) -----------------------------------------

    async def _current_bank(
        self, session: AsyncSession, code: str | None = None
    ) -> QuestionnaireTemplate:
        stmt = select(QuestionnaireTemplate)
        stmt = (
            stmt.where(QuestionnaireTemplate.code == code)
            if code
            else stmt.where(QuestionnaireTemplate.is_current.is_(True))
        )
        bank = (await session.execute(stmt.limit(1))).scalar_one_or_none()
        if bank is None:
            raise InvalidInput(
                "No questionnaire bank is available. Ask an administrator to load the "
                "shipped content.",
                detail=f"no questionnaire_template for code={code!r}",
            )
        return bank

    async def _bank_questions(
        self, session: AsyncSession, template_id: uuid.UUID, scope_levels: Sequence[str]
    ) -> list[QuestionnaireQuestion]:
        stmt = (
            select(QuestionnaireQuestion)
            .where(QuestionnaireQuestion.template_id == template_id)
            .where(QuestionnaireQuestion.scope_level.in_(list(scope_levels)))
            .order_by(QuestionnaireQuestion.position)
        )
        return list((await session.execute(stmt)).scalars())

    async def issue_questionnaire(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        engagement_id: uuid.UUID,
        contact_id: uuid.UUID | None = None,
        due_date: date | None = None,
        bank_code: str | None = None,
    ) -> IssuedQuestionnaire:
        """Create the assessment, mint the portal link, and tell the contact.

        The question set is chosen by the engagement's tier and **snapshotted onto
        the assessment**. The bank is versioned global content that can change
        under a vendor mid-answer, and a residual score computed against a
        question set nobody can reconstruct is not defensible.

        The token is returned exactly once, here, in the link. It is stored only as
        a hash, so nothing downstream — not this service, not the database, not a
        backup — can produce it again.
        """
        engagement = await self._load_engagement(session, tenant_id, engagement_id)
        if engagement.vendor_id != vendor_id:
            raise NotFound(
                _ENGAGEMENT_GONE, detail=f"engagement {engagement_id} is not on {vendor_id}"
            )
        vendor = await self._load(session, tenant_id, vendor_id)
        if engagement.tier is None:
            raise Conflict(
                "Tier this engagement before sending a questionnaire. The tier is what "
                "decides which questions are asked.",
                detail=f"engagement {engagement_id} has no tier",
            )

        contact = await self._portal_contact(session, tenant_id, vendor.id, contact_id)
        bank = await self._current_bank(session, bank_code)
        levels = BUNDLE_BY_TIER.get(engagement.tier, ("lite",))
        questions = await self._bank_questions(session, bank.id, levels)
        if not questions:
            raise InvalidInput(
                "That questionnaire bank has no questions for this tier.",
                detail=f"bank {bank.code} has no questions at levels {levels}",
            )

        cycle = await self._current_cycle(session, tenant_id, engagement.id)
        now = datetime.now(UTC)

        # Re-issuing is a *resend*, not a second review. An open assessment for
        # this cycle is refreshed in place and gets a new link; creating another
        # would duplicate every response row, leave two live tokens, and make the
        # register count one questionnaire as two.
        open_already = await self._open_assessment(session, tenant_id, engagement.id, cycle)
        if open_already is not None:
            open_already.portal_contact_id = contact.id
            open_already.due_date = due_date or open_already.due_date
            token = await self._mint_portal_token(session, tenant_id, open_already)
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_assessment",
                object_id=open_already.id,
                actor=actor,
                tenant_id=tenant_id,
                before={"portal_link": "issued"},
                after={"portal_link": "reissued", "contact_id": str(contact.id)},
            )
            await self._send_portal_invitation(vendor, contact, open_already, token)
            await session.flush()
            return IssuedQuestionnaire(
                assessment_id=open_already.id,
                contact_email=contact.email or "",
                question_count=int(open_already.scope.get("question_count", 0)),
                due_date=open_already.due_date,
                portal_url=_portal_url(token),
            )

        assessment = VendorAssessment(
            id=uuid7(),
            tenant_id=tenant_id,
            vendor_id=vendor.id,
            engagement_id=engagement.id,
            template_id=bank.id,
            cycle=cycle,
            kind="reassessment" if cycle > 1 else "initial",
            status="pending",
            due_date=due_date or (now.date() + timedelta(days=_QUESTIONNAIRE_DUE_DAYS)),
            portal_contact_id=contact.id,
            scope={
                "bank_code": bank.code,
                "bank_version": bank.version,
                "tier": engagement.tier,
                "scope_levels": list(levels),
                "question_codes": [q.code for q in questions],
                "question_count": len(questions),
                "snapshotted_at": now.isoformat(),
            },
        )
        session.add(assessment)
        await session.flush([assessment])

        # One row per question, unanswered. The portal then updates rows rather
        # than inventing them, so a question that was asked and ignored is
        # distinguishable from one that was never asked.
        for question in questions:
            session.add(
                VendorAssessmentResponse(
                    id=uuid7(),
                    tenant_id=tenant_id,
                    assessment_id=assessment.id,
                    question_id=question.id,
                )
            )
        await session.flush()

        token = await self._mint_portal_token(session, tenant_id, assessment)
        await self._audit.record(
            session,
            action="create",
            object_type="vendor_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before=None,
            after={
                "vendor_id": str(vendor.id),
                "bank": bank.code,
                "tier": engagement.tier,
                "question_count": len(questions),
                "contact_id": str(contact.id),
            },
        )
        await self._send_portal_invitation(vendor, contact, assessment, token)
        await session.flush()
        return IssuedQuestionnaire(
            assessment_id=assessment.id,
            contact_email=contact.email or "",
            question_count=len(questions),
            due_date=assessment.due_date,
            portal_url=_portal_url(token),
        )

    async def _open_assessment(
        self, session: AsyncSession, tenant_id: uuid.UUID, engagement_id: uuid.UUID, cycle: int
    ) -> VendorAssessment | None:
        """An assessment for this cycle that has not been handed back yet."""
        return (
            await session.execute(
                select(VendorAssessment)
                .where(VendorAssessment.tenant_id == tenant_id)
                .where(VendorAssessment.engagement_id == engagement_id)
                .where(VendorAssessment.cycle == cycle)
                .where(VendorAssessment.status.in_(["pending", "in_progress"]))
                .order_by(VendorAssessment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _portal_contact(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        contact_id: uuid.UUID | None,
    ) -> VendorContact:
        stmt = (
            select(VendorContact)
            .where(VendorContact.tenant_id == tenant_id)
            .where(VendorContact.vendor_id == vendor_id)
        )
        if contact_id is not None:
            stmt = stmt.where(VendorContact.id == contact_id)
        else:
            stmt = stmt.where(VendorContact.contact_type == "portal")
        contact = (await session.execute(stmt.limit(1))).scalar_one_or_none()
        if contact is None:
            raise InvalidInput(
                "This vendor has no portal contact to send the questionnaire to. "
                "Add one with an email address first.",
                detail=f"no portal contact on vendor {vendor_id}",
            )
        if not contact.email:
            raise InvalidInput(
                f"{contact.name} has no email address, so the questionnaire link has "
                "nowhere to go.",
                detail=f"contact {contact.id} has no email",
            )
        return contact

    async def _mint_portal_token(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment: VendorAssessment
    ) -> str:
        """Issue a token, store only its hash, and revoke any that came before.

        Revocation is a write rather than a delete, so "a link was sent on Tuesday
        and replaced on Friday" stays answerable. Re-issuing therefore invalidates
        the old link, which is the behaviour somebody expects from a resend.
        """
        now = datetime.now(UTC)
        stale = (
            await session.execute(
                select(VendorPortalToken)
                .where(VendorPortalToken.tenant_id == tenant_id)
                .where(VendorPortalToken.assessment_id == assessment.id)
                .where(VendorPortalToken.revoked_at.is_(None))
            )
        ).scalars()
        for row in stale:
            row.revoked_at = now

        token = ratelimit.new_opaque_token()
        session.add(
            VendorPortalToken(
                id=uuid7(),
                token_hash=ratelimit.hash_token(token),
                tenant_id=tenant_id,
                assessment_id=assessment.id,
                expires_at=now + timedelta(days=_PORTAL_TOKEN_DAYS),
            )
        )
        await session.flush()
        return token

    async def _send_portal_invitation(
        self,
        vendor: Vendor,
        contact: VendorContact,
        assessment: VendorAssessment,
        token: str,
    ) -> None:
        """Email the link. A vendor contact is not a member, so this goes through
        the mailer directly — ``notification_service`` targets memberships only, and
        inventing a membership for an outsider would break rule 3."""
        from verity.core.email import OutboundEmail, get_mailer  # noqa: PLC0415

        due = assessment.due_date.isoformat() if assessment.due_date else "shortly"
        count = int(assessment.scope.get("question_count", 0))
        text = (
            f"Security review for {vendor.name}\n\n"
            f"{contact.name}, we are reviewing the security of the services "
            f"{vendor.name} provides to us, and would like you to complete a short "
            f"questionnaire — {count} questions.\n\n"
            f"{_portal_url(token)}\n\n"
            f"The link is personal to this review, expires in {_PORTAL_TOKEN_DAYS} days, "
            f"and does not need an account. Please complete it by {due}.\n"
        )
        await get_mailer().send(
            OutboundEmail(
                to=contact.email or "",
                subject=f"Security review questionnaire for {vendor.name}",
                text=text,
            )
        )

    # -- scoring the review (V7) ----------------------------------------------

    async def score_assessment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        assessment_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
    ) -> AssessmentView:
        """Roll the answers into a residual score, and raise findings from the noes.

        Scoring and finding-raising are one transaction on purpose: a score with no
        findings behind it is a number nobody can act on, and findings with no score
        are a list nobody can prioritise.
        """
        assessment = await self._load_assessment(session, tenant_id, assessment_id)
        if vendor_id is not None and assessment.vendor_id != vendor_id:
            raise NotFound(
                _ASSESSMENT_GONE, detail=f"assessment {assessment_id} is not on vendor {vendor_id}"
            )
        engagement = await self._load_engagement(session, tenant_id, assessment.engagement_id)
        rows = await self.answers_with_questions(
            session, tenant_id=tenant_id, assessment_id=assessment.id
        )
        if not rows:
            raise Conflict(
                "There is nothing to score yet — this questionnaire has no questions.",
                detail=f"assessment {assessment_id} has no responses",
            )

        tiering = await self._latest_tiering(session, tenant_id, engagement.id, assessment.cycle)
        inherent = tiering.inherent_score if tiering else 0.0
        breakdown = scoring.compute_residual(
            [
                scoring.Answer(
                    question_key=question.code,
                    domain=question.domain,
                    answer=response.answer or "",
                    weight=question.weight,
                    critical_control=question.critical_control,
                )
                for response, question in rows
            ],
            inherent=inherent,
        )

        # Read before the write, rather than asserting what it must have been.
        was = {
            "status": assessment.status,
            "residual_score": assessment.residual_score,
            "grade": assessment.grade,
        }
        assessment.residual_score = breakdown.score
        assessment.grade = breakdown.grade
        assessment.domain_scores = {
            d.domain: {"posture": d.posture, "residual": d.residual, "answered": d.answered}
            for d in breakdown.domains
        }
        assessment.score_snapshot = {
            "inherent": breakdown.inherent,
            "control_ceiling": scoring.CONTROL_CEILING,
            "domain_weights": scoring.DEFAULT_DOMAIN_WEIGHTS,
            "steps": [
                {"label": s.label, "value": s.value, "detail": s.detail} for s in breakdown.steps
            ],
        }
        assessment.status = "scored"

        raised = await self._raise_findings(session, tenant_id, actor, assessment, rows)
        await self._recache_residual(session, tenant_id, assessment)

        await self._audit.record(
            session,
            action="update",
            object_type="vendor_assessment",
            object_id=assessment.id,
            actor=actor,
            tenant_id=tenant_id,
            before=was,
            after={
                "status": "scored",
                "residual_score": breakdown.score,
                "grade": breakdown.grade,
                "findings_raised": raised,
            },
        )
        await session.flush()
        return await self.get_assessment(session, tenant_id=tenant_id, assessment_id=assessment.id)

    async def _raise_findings(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor: Actor,
        assessment: VendorAssessment,
        rows: Sequence[tuple[VendorAssessmentResponse, QuestionnaireQuestion]],
    ) -> int:
        """One finding per ``no``, severity from what the question is.

        Idempotent per (assessment, question): re-scoring after a corrected answer
        updates the finding rather than raising a second one, and a question whose
        answer has changed away from ``no`` closes the finding it caused.
        """
        existing = {
            row.question_id: row
            for row in (
                await session.execute(
                    select(VendorFinding)
                    .where(VendorFinding.tenant_id == tenant_id)
                    .where(VendorFinding.assessment_id == assessment.id)
                )
            ).scalars()
        }
        raised = 0
        now = datetime.now(UTC)
        for response, question in rows:
            failed = response.answer == "no"
            found = existing.get(question.id)
            if not failed:
                if found is not None and found.status in OPEN_FINDING_STATUSES:
                    before = AuditService.snapshot(found, fields=_FINDING_SNAPSHOT)
                    found.status = "closed"
                    found.closed_at = now
                    # Its own row, naming the finding. A corrected answer closing a
                    # finding is a state change on that finding, and rolling it up
                    # into a count on the assessment loses which one moved.
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="vendor_finding",
                        object_id=found.id,
                        actor=actor,
                        tenant_id=tenant_id,
                        before=before,
                        after={
                            **AuditService.snapshot(found, fields=_FINDING_SNAPSHOT),
                            "reason": "the answer that raised it changed",
                        },
                    )
                continue
            severity = _finding_severity(question)
            if found is not None:
                before = AuditService.snapshot(found, fields=_FINDING_SNAPSHOT)
                found.severity = severity
                found.is_blocking = question.non_negotiable
                after = AuditService.snapshot(found, fields=_FINDING_SNAPSHOT)
                if before != after:
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="vendor_finding",
                        object_id=found.id,
                        actor=actor,
                        tenant_id=tenant_id,
                        before=before,
                        after=after,
                    )
                continue
            new_finding = VendorFinding(
                id=uuid7(),
                tenant_id=tenant_id,
                vendor_id=assessment.vendor_id,
                engagement_id=assessment.engagement_id,
                assessment_id=assessment.id,
                question_id=question.id,
                title=_finding_title(question),
                detail=question.body,
                finding_source="assessment",
                severity=severity,
                is_blocking=question.non_negotiable,
                sla_due=now.date() + timedelta(days=_FINDING_SLA_DAYS[severity]),
            )
            session.add(new_finding)
            await session.flush([new_finding])
            await self._audit.record(
                session,
                action="create",
                object_type="vendor_finding",
                object_id=new_finding.id,
                actor=actor,
                tenant_id=tenant_id,
                before=None,
                after=AuditService.snapshot(new_finding, fields=_FINDING_SNAPSHOT),
            )
            raised += 1
        await session.flush()
        return raised

    async def _recache_residual(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment: VendorAssessment
    ) -> None:
        """Refresh the vendor's cached worst residual and grade (V10).

        Worst means highest score, and the grade is taken from the same assessment
        rather than computed separately — a vendor showing a score from one
        engagement and a grade from another would be quietly incoherent.
        """
        rows = list(
            (
                await session.execute(
                    select(VendorAssessment)
                    .where(VendorAssessment.tenant_id == tenant_id)
                    .where(VendorAssessment.vendor_id == assessment.vendor_id)
                    .where(VendorAssessment.residual_score.is_not(None))
                )
            ).scalars()
        )
        if not rows:
            return
        worst = max(rows, key=lambda a: a.residual_score or 0.0)
        vendor = await self._load(session, tenant_id, assessment.vendor_id)
        vendor.current_residual_score = worst.residual_score
        vendor.current_grade = worst.grade

    # -- reading the review ----------------------------------------------------

    async def _load_assessment(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> VendorAssessment:
        row = await session.get(VendorAssessment, assessment_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_ASSESSMENT_GONE, detail=f"vendor assessment {assessment_id}")
        return row

    async def answers_with_questions(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> list[tuple[VendorAssessmentResponse, QuestionnaireQuestion]]:
        """The assessment's rows joined to their questions, in asked order."""
        stmt = (
            select(VendorAssessmentResponse, QuestionnaireQuestion)
            .join(
                QuestionnaireQuestion,
                QuestionnaireQuestion.id == VendorAssessmentResponse.question_id,
            )
            .where(VendorAssessmentResponse.tenant_id == tenant_id)
            .where(VendorAssessmentResponse.assessment_id == assessment_id)
            .order_by(QuestionnaireQuestion.position)
        )
        return [(r, q) for r, q in (await session.execute(stmt)).all()]

    @staticmethod
    def _response_view(
        response: VendorAssessmentResponse, question: QuestionnaireQuestion
    ) -> ResponseView:
        return ResponseView(
            id=response.id,
            question_id=question.id,
            question_code=question.code,
            body=question.body,
            domain=question.domain,
            domain_label=RISK_DOMAIN_LABELS[question.domain],
            scope_level=question.scope_level,
            answer_type=question.answer_type,
            weight=question.weight,
            critical_control=question.critical_control,
            non_negotiable=question.non_negotiable,
            evidence_required=question.evidence_required,
            framework_refs=list(question.framework_refs or []),
            answer=response.answer,
            implementation_notes=response.implementation_notes,
            na_justification=response.na_justification,
            evidence_id=response.evidence_id,
            answered_at=response.answered_at,
        )

    def _assessment_view(
        self,
        assessment: VendorAssessment,
        responses: Sequence[tuple[VendorAssessmentResponse, QuestionnaireQuestion]],
        findings: Sequence[VendorFinding],
        names: dict[uuid.UUID, str],
        token: VendorPortalToken | None,
    ) -> AssessmentView:
        answered = sum(1 for r, _ in responses if r.answer)
        missing_evidence = sum(
            1
            for r, q in responses
            if q.evidence_required and r.answer == "yes" and not r.evidence_id
        )
        return AssessmentView(
            id=assessment.id,
            vendor_id=assessment.vendor_id,
            engagement_id=assessment.engagement_id,
            cycle=assessment.cycle,
            kind=assessment.kind,
            review_format=assessment.review_format,
            assessment_domain=assessment.assessment_domain,
            status=assessment.status,
            decision=assessment.decision,
            due_date=assessment.due_date,
            residual_score=assessment.residual_score,
            grade=assessment.grade,
            domain_scores=dict(assessment.domain_scores or {}),
            score_steps=list((assessment.score_snapshot or {}).get("steps", [])),
            scope=dict(assessment.scope or {}),
            question_count=len(responses),
            answered_count=answered,
            unanswered_count=len(responses) - answered,
            missing_evidence_count=missing_evidence,
            submitted_at=assessment.submitted_at,
            responses=[self._response_view(r, q) for r, q in responses],
            findings=[self._finding_view(f, names) for f in findings],
            portal_link_live=bool(
                token and token.revoked_at is None and token.expires_at > datetime.now(UTC)
            ),
            portal_link_expires_at=token.expires_at if token else None,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
        )

    @staticmethod
    def _finding_view(finding: VendorFinding, names: dict[uuid.UUID, str]) -> FindingView:
        owner = finding.owner_membership_id
        return FindingView(
            id=finding.id,
            vendor_id=finding.vendor_id,
            assessment_id=finding.assessment_id,
            question_id=finding.question_id,
            title=finding.title,
            detail=finding.detail,
            finding_source=finding.finding_source,
            severity=finding.severity,
            status=finding.status,
            treatment=finding.treatment,
            is_blocking=finding.is_blocking,
            sla_due=finding.sla_due,
            owner_membership_id=owner,
            owner_name=names.get(owner) if owner else None,
            task_id=finding.task_id,
            accepted_until=finding.accepted_until,
            accepted_rationale=finding.accepted_rationale,
            closed_at=finding.closed_at,
            # The seam to modules/risk, which has no tables. Always None today.
            promoted_risk_id=finding.promoted_risk_id,
            created_at=finding.created_at,
        )

    async def _live_token(
        self, session: AsyncSession, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> VendorPortalToken | None:
        return (
            await session.execute(
                select(VendorPortalToken)
                # Explicit, and load-bearing: this table has no policy, so the
                # filter is the only wall rather than the first of two.
                .where(VendorPortalToken.tenant_id == tenant_id)
                .where(VendorPortalToken.assessment_id == assessment_id)
                .where(VendorPortalToken.revoked_at.is_(None))
                .order_by(VendorPortalToken.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_assessment(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> AssessmentView:
        assessment = await self._load_assessment(session, tenant_id, assessment_id)
        responses = await self.answers_with_questions(
            session, tenant_id=tenant_id, assessment_id=assessment.id
        )
        findings = list(
            (
                await session.execute(
                    select(VendorFinding)
                    .where(VendorFinding.tenant_id == tenant_id)
                    .where(VendorFinding.assessment_id == assessment.id)
                    .order_by(VendorFinding.created_at)
                )
            ).scalars()
        )
        names = await self._member_names(session, tenant_id)
        token = await self._live_token(session, tenant_id, assessment.id)
        return self._assessment_view(assessment, responses, findings, names, token)

    async def list_findings(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        statuses: tuple[str, ...] = (),
    ) -> list[FindingView]:
        stmt = select(VendorFinding).where(VendorFinding.tenant_id == tenant_id)
        if vendor_id is not None:
            stmt = stmt.where(VendorFinding.vendor_id == vendor_id)
        if statuses:
            stmt = stmt.where(VendorFinding.status.in_(list(statuses)))
        rows = list((await session.execute(stmt)).scalars())
        names = await self._member_names(session, tenant_id)
        views = [self._finding_view(f, names) for f in rows]
        views.sort(key=lambda f: (FINDING_SEVERITIES.index(f.severity), f.sla_due or date.max))
        return views

    async def open_critical_count(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> int:
        """What the findings stage and the approval gate ask for.

        An accepted risk does not count as open: acceptance is a decision somebody
        made and time-boxed, not an outstanding item.
        """
        return (
            await session.execute(
                select(func.count())
                .select_from(VendorFinding)
                .where(VendorFinding.tenant_id == tenant_id)
                .where(VendorFinding.vendor_id == vendor_id)
                .where(VendorFinding.severity == "critical")
                .where(VendorFinding.status.in_(list(OPEN_FINDING_STATUSES)))
            )
        ).scalar_one()

    async def tenant_display_name(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> str:
        """The organisation's own name, for the portal page.

        A vendor contact opening a link should see who is asking. Read through the
        tenancy service rather than the table (rule 4), and degraded to a neutral
        word rather than raising: a missing display name must not take the
        questionnaire down.
        """
        from verity.modules.tenancy.service import tenancy_service  # noqa: PLC0415

        try:
            profile = await tenancy_service.get_tenant(session, tenant_id)
        except Exception:
            return "our organisation"
        return getattr(profile, "name", None) or "our organisation"

    # -- acting on a finding ---------------------------------------------------

    async def _load_finding(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
    ) -> VendorFinding:
        row = await session.get(VendorFinding, finding_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id or row.vendor_id != vendor_id:
            raise NotFound(_FINDING_GONE, detail=f"vendor finding {finding_id} on {vendor_id}")
        return row

    async def remediate_finding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
        owner_membership_id: uuid.UUID | None = None,
        due_at: datetime | None = None,
    ) -> FindingView:
        """Open a real task for the fix, in the tasks module.

        Not a vendor-local to-do table. The tasks module already carries
        assignment, SLA, transitions and CAPA, and a second worse one here would be
        invisible to every dashboard that counts work.
        """
        finding = await self._load_finding(session, tenant_id, vendor_id, finding_id)
        if finding.task_id is not None:
            raise Conflict(
                "This finding already has a remediation task open.",
                detail=f"finding {finding_id} already linked to task {finding.task_id}",
            )
        if finding.status not in OPEN_FINDING_STATUSES:
            raise Conflict(
                "This finding is closed. Reopen it before planning remediation.",
                detail=f"finding {finding_id} is {finding.status}",
            )
        vendor = await self._load(session, tenant_id, finding.vendor_id)

        from verity.modules.tasks.service import task_service  # noqa: PLC0415

        task = await task_service.create_task(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task_kind="issue",
            title=f"{vendor.name}: {finding.title}",
            description=finding.detail,
            priority=_TASK_PRIORITY[finding.severity],
            category="vendor",
            owner_membership_id=owner_membership_id or finding.owner_membership_id,
            due_at=due_at
            or (
                datetime.combine(finding.sla_due, datetime.min.time(), tzinfo=UTC)
                if finding.sla_due
                else None
            ),
            raised_from_type="vendor_finding",
        )
        before = AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT)
        finding.task_id = task.id
        finding.status = "in_remediation"
        finding.treatment = "remediate"
        if owner_membership_id is not None:
            finding.owner_membership_id = owner_membership_id
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_finding",
            object_id=finding.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT),
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._finding_view(finding, names)

    async def accept_finding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
        until: date,
        rationale: str,
    ) -> FindingView:
        """Accept the risk, for a stated time and a stated reason.

        Both are required, and the expiry must be in the future: an open-ended
        acceptance is a risk nobody will look at again, which is the failure this
        whole record exists to prevent.
        """
        finding = await self._load_finding(session, tenant_id, vendor_id, finding_id)
        if not rationale.strip():
            raise InvalidInput(
                "Say why this risk is acceptable. The rationale is what a reviewer "
                "reads when the acceptance comes up for renewal.",
                detail="acceptance without a rationale",
            )
        if until <= datetime.now(UTC).date():
            raise InvalidInput(
                "The acceptance has to expire in the future. Pick a review date.",
                detail=f"accepted_until {until} is not in the future",
            )
        before = AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT)
        finding.status = "accepted"
        finding.treatment = "accept"
        finding.accepted_until = until
        finding.accepted_rationale = rationale.strip()
        finding.accepted_by_membership_id = actor.id if isinstance(actor, Membership) else None
        await self._audit.record(
            session,
            action="approve",
            object_type="vendor_finding",
            object_id=finding.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT),
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._finding_view(finding, names)

    async def close_finding(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        vendor_id: uuid.UUID,
        finding_id: uuid.UUID,
        note: str | None = None,
    ) -> FindingView:
        finding = await self._load_finding(session, tenant_id, vendor_id, finding_id)
        before = AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT)
        finding.status = "closed"
        finding.closed_at = datetime.now(UTC)
        await self._audit.record(
            session,
            action="update",
            object_type="vendor_finding",
            object_id=finding.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after={**AuditService.snapshot(finding, fields=_FINDING_SNAPSHOT), "note": note},
        )
        await session.flush()
        names = await self._member_names(session, tenant_id)
        return self._finding_view(finding, names)


vendor_service = VendorService()
