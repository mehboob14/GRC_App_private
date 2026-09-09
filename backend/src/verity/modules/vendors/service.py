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
from datetime import date, datetime
from typing import Any, Final

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import InvalidInput, NotFound
from verity.modules.audit.service import Actor, AuditService, audit_service
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
        return {
            "vendor_types": list(VENDOR_TYPES),
            "statuses": list(LIFECYCLE_STATUSES),
            "tiers": list(TIERS),
            "classifications": list(DATA_CLASSIFICATIONS),
            "contact_types": list(CONTACT_TYPES),
            "business_units": [u for u in units if u],
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


vendor_service = VendorService()
