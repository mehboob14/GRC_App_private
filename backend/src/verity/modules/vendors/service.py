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
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, Membership, audit_service
from verity.modules.vendors import lifecycle, scoring
from verity.modules.vendors.models import (
    CONTACT_TYPES,
    DATA_CLASSIFICATIONS,
    DEFAULT_ENGAGEMENT_NAME,
    LIFECYCLE_STATUSES,
    TIERS,
    VENDOR_TYPES,
    Vendor,
    VendorContact,
    VendorEngagement,
    VendorStage,
    VendorTieringAssessment,
    VendorTieringPolicy,
    VendorTransition,
)
from verity.shared.ids import uuid7

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


vendor_service = VendorService()
