"""Risk register business logic.

DB access lives here (no separate repository, matching the tasks, assets and
vendors modules). Pure rules are in ``scoring``; spreadsheets in ``transfer``;
the AI draft in ``assist``.

Every state change writes a ``risk_events`` row (the history the detail page
renders) and an ``audit_log`` row (rule 5), in the caller's transaction.
Cross-module reads and writes go through sibling services (rule 4): member and
group names through IAM, controls through compliance, treatment actions through
tasks, links through the links primitive, labels through each owning module.
"""

from __future__ import annotations

import contextlib
import re
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from sqlalchemy import Select, and_, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.errors import Conflict, InvalidInput, NotFound, PermissionDenied
from verity.modules.audit.service import (
    Actor,
    AuditService,
    Membership,
    System,
    audit_service,
)
from verity.modules.customfields.service import (
    FieldDefinition,
    FieldInput,
    custom_field_service,
)
from verity.modules.risk import scoring
from verity.modules.risk.models import (
    ACCEPTANCE_STATUSES,
    ORIGINS,
    REGISTER_TYPES,
    RISK_STATUSES,
    TREATMENTS,
    Risk,
    RiskAcceptance,
    RiskCategory,
    RiskControlMap,
    RiskEvent,
    RiskRegister,
    RiskTemplate,
)
from verity.shared.ids import uuid7

_RISK_GONE: Final = "This risk no longer exists. It may have been removed."
_REGISTER_GONE: Final = "This register no longer exists."
_ACCEPTANCE_GONE: Final = "This acceptance no longer exists."
_CODE_PREFIX: Final = "RSK-"
_CODE_RE: Final = re.compile(r"^RSK-(\d+)$")
_EXPIRY_WARNING_DAYS: Final = 30
_MAX_PAGE_SIZE: Final = 200
_DEFAULT_CATEGORY: Final = "Operational"
_TOP_RISKS: Final = 5

# Record types a risk links to through the links primitive. Controls use their
# own join table (ER RISK_CONTROL_MAP), so they are not in this list.
LINKABLE_TYPES: Final[tuple[str, ...]] = (
    "asset",
    "vulnerability",
    "evidence",
    "task",
    "vendor",
    "document",
)

# Which task category a treatment action lands in, by register type.
_ACTION_CATEGORY: Final[dict[str, str]] = {
    "gdpr": "privacy",
    "sox": "regulatory",
    "pci_dss": "regulatory",
    "third_party": "vendor",
    "project": "operations",
    "rcsa": "operations",
}

_REGISTER_SNAPSHOT: Final[tuple[str, ...]] = (
    "name",
    "register_type",
    "description",
    "owner_membership_id",
    "is_default",
    "status",
    "likelihood_levels",
    "impact_levels",
    "likelihood_scale",
    "impact_scale",
    "severity_bands",
    "review_cadence_days",
    "scoring_formula",
    "appetite",
)
"""Named rather than every column: ``updated_at`` is refreshed by the database on
flush, and reading an expired attribute outside the async context fails."""

_SNAPSHOT_FIELDS: Final[tuple[str, ...]] = (
    "code",
    "title",
    "status",
    "treatment",
    "category_id",
    "sub_category_id",
    "inherent_likelihood",
    "inherent_impact",
    "residual_likelihood",
    "residual_impact",
    "owner_membership_id",
    "department_group_id",
    "treatment_due_on",
    "next_review_on",
)


# -- views -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CategoryView:
    id: uuid.UUID
    name: str
    position: int
    archived: bool
    risk_count: int
    children: list[CategoryView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RegisterView:
    id: uuid.UUID
    name: str
    register_type: str
    description: str | None
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    is_default: bool
    status: str
    likelihood_levels: int
    impact_levels: int
    likelihood_scale: list[dict[str, Any]]
    impact_scale: list[dict[str, Any]]
    severity_bands: list[dict[str, Any]]
    review_cadence_days: int
    risk_count: int
    categories: list[CategoryView]
    created_at: datetime
    scoring_formula: dict[str, Any] = field(default_factory=lambda: {"method": "product"})
    appetite: dict[str, Any] = field(default_factory=dict)
    max_score: int = 25


@dataclass(frozen=True, slots=True)
class Person:
    membership_id: uuid.UUID
    name: str


@dataclass(frozen=True, slots=True)
class RiskView:
    id: uuid.UUID
    register_id: uuid.UUID
    code: str
    title: str
    description: str
    category_id: uuid.UUID
    category_name: str
    sub_category_id: uuid.UUID | None
    sub_category_name: str | None
    status: str
    treatment: str | None
    inherent_likelihood: int | None
    inherent_impact: int | None
    inherent_score: int | None
    inherent_band: str | None
    residual_likelihood: int | None
    residual_impact: int | None
    residual_score: int | None
    residual_band: str | None
    owner: Person | None
    department_group_id: uuid.UUID | None
    department_name: str | None
    treatment_due_on: date | None
    next_review_on: date | None
    last_reviewed_at: datetime | None
    origin: str
    control_count: int
    attention: list[str]
    created_at: datetime
    updated_at: datetime
    appetite_status: str | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlRefView:
    id: uuid.UUID
    code: str
    name: str
    status: str
    category: str
    disabled: bool


@dataclass(frozen=True, slots=True)
class LinkedRecordView:
    link_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relation: str
    code: str
    title: str
    status: str
    detail: str | None


@dataclass(frozen=True, slots=True)
class ActionView:
    link_id: uuid.UUID
    task_id: uuid.UUID
    code: str
    title: str
    status: str
    priority: str
    owner_name: str | None
    due_at: datetime | None


@dataclass(frozen=True, slots=True)
class AcceptanceView:
    id: uuid.UUID
    status: str
    rationale: str
    expires_on: date
    requested_by: Person | None
    approver: Person | None
    residual_score_at_request: int | None
    decided_at: datetime | None
    decision_note: str | None
    revoked_at: datetime | None
    revoke_reason: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EventView:
    id: uuid.UUID
    kind: str
    from_value: str | None
    to_value: str | None
    note: str | None
    inherent_score: int | None
    residual_score: int | None
    actor_name: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RiskDetailView(RiskView):
    root_cause: str | None = None
    consequences: str | None = None
    recommendations: str | None = None
    treatment_plan: str | None = None
    closure_justification: str | None = None
    closed_at: datetime | None = None
    template_code: str | None = None
    origin_ref: uuid.UUID | None = None
    created_by_name: str | None = None
    allowed_statuses: list[str] = field(default_factory=list)
    controls: list[ControlRefView] = field(default_factory=list)
    links: list[LinkedRecordView] = field(default_factory=list)
    actions: list[ActionView] = field(default_factory=list)
    acceptances: list[AcceptanceView] = field(default_factory=list)
    history: list[EventView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ApproverView:
    membership_id: uuid.UUID
    name: str
    eligible: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class TemplateView:
    id: uuid.UUID
    code: str
    title: str
    description: str
    category: str
    sub_category: str | None
    default_likelihood: int
    default_impact: int
    root_cause: str | None
    consequences: str | None
    recommendations: str | None
    treatment: str | None
    control_keys: list[str]
    frameworks: list[str]
    adopted: bool


@dataclass(frozen=True, slots=True)
class RiskRef:
    id: uuid.UUID
    code: str
    title: str
    status: str
    band: str | None
    register_name: str


# -- inputs ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegisterInput:
    name: str
    register_type: str = "enterprise"
    description: str | None = None
    owner_membership_id: uuid.UUID | None = None
    likelihood_levels: int | None = None
    impact_levels: int | None = None
    likelihood_scale: list[dict[str, Any]] | None = None
    impact_scale: list[dict[str, Any]] | None = None
    severity_bands: list[dict[str, Any]] | None = None
    review_cadence_days: int | None = None
    is_default: bool | None = None
    status: str | None = None
    scoring_formula: dict[str, Any] | None = None
    appetite: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CategoryNode:
    name: str
    id: uuid.UUID | None = None
    children: list[CategoryNode] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RiskInput:
    register_id: uuid.UUID
    title: str
    category_id: uuid.UUID
    description: str = ""
    sub_category_id: uuid.UUID | None = None
    status: str = "open"
    treatment: str | None = None
    inherent_likelihood: int | None = None
    inherent_impact: int | None = None
    residual_likelihood: int | None = None
    residual_impact: int | None = None
    root_cause: str | None = None
    consequences: str | None = None
    recommendations: str | None = None
    treatment_plan: str | None = None
    owner_membership_id: uuid.UUID | None = None
    department_group_id: uuid.UUID | None = None
    treatment_due_on: date | None = None
    next_review_on: date | None = None
    # None on update means "leave the asset links alone"; a list replaces them.
    asset_ids: list[uuid.UUID] | None = None
    # None on update leaves the extras alone; a dict is validated against the definitions.
    custom_fields: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class RiskFilters:
    register_id: uuid.UUID
    search: str | None = None
    statuses: tuple[str, ...] = ()
    bands: tuple[str, ...] = ()
    category_ids: tuple[uuid.UUID, ...] = ()
    treatments: tuple[str, ...] = ()
    owner: str | None = None  # "me" | "unassigned" | membership uuid
    department_ids: tuple[uuid.UUID, ...] = ()
    attention: tuple[str, ...] = ()
    cell: str | None = None  # "inherent:L:I" | "residual:L:I"
    include_closed: bool = True
    custom: tuple[tuple[str, str], ...] = ()  # (field key, value)


_SORTS: Final[tuple[str, ...]] = (
    "code",
    "title",
    "inherent",
    "residual",
    "status",
    "next_review",
    "updated",
)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _actor_id(actor: Actor) -> uuid.UUID | None:
    return actor.id if isinstance(actor, Membership) else None


def _pair(likelihood: int | None, impact: int | None) -> str | None:
    return None if likelihood is None or impact is None else f"{likelihood}×{impact}"  # noqa: RUF001 — shown to people


class RiskService:
    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- cross-module resolution (rule 4) -------------------------------------

    async def _member_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        members = await iam_service.list_members(session, tenant_id=tenant_id)
        return {m.membership_id: m.full_name for m in members}

    async def _group_names(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        groups = await iam_service.list_groups(session, tenant_id=tenant_id)
        return {g.id: g.name for g in groups}

    async def members(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> list[Any]:
        """Workspace members (IAM ``MemberView``), for import matching by email."""
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        return list(await iam_service.list_members(session, tenant_id=tenant_id))

    async def form_options(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[str, Any]:
        """Owners and business units for the risk form, under ``risks:read``, so a
        risk manager needs neither the members nor the groups permission."""
        members = await self.members(session, tenant_id=tenant_id)
        groups = await self._group_names(session, tenant_id)
        return {
            "members": sorted(
                (
                    {"membership_id": m.membership_id, "name": m.full_name, "email": m.email}
                    for m in members
                    if m.status == "active"
                ),
                key=lambda m: str(m["name"]).lower(),
            ),
            "business_units": sorted(
                ({"id": gid, "name": name} for gid, name in groups.items()),
                key=lambda g: str(g["name"]).lower(),
            ),
        }

    async def groups(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
        return await self._group_names(session, tenant_id)

    async def register_context(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> tuple[RiskRegister, list[RiskCategory]]:
        """The register row and its taxonomy rows, for import and assist."""
        register = await self._load_register(session, tenant_id, register_id)
        return register, await self._categories(session, tenant_id, register.id)

    async def titles(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> set[str]:
        rows = await session.execute(
            select(func.lower(Risk.title)).where(
                Risk.tenant_id == tenant_id, Risk.register_id == register_id
            )
        )
        return set(rows.scalars())

    async def next_code_number(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
        return await self._next_code(session, tenant_id)

    async def active_acceptances(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        names = await self._member_names(session, tenant_id)
        rows = await session.execute(
            select(
                Risk.code,
                Risk.title,
                RiskAcceptance.expires_on,
                RiskAcceptance.approver_membership_id,
            )
            .join(Risk, Risk.id == RiskAcceptance.risk_id)
            .where(
                RiskAcceptance.tenant_id == tenant_id,
                RiskAcceptance.status == "active",
                Risk.register_id == register_id,
            )
            .order_by(RiskAcceptance.expires_on)
        )
        return [
            {
                "code": code,
                "title": title,
                "expires_on": expires_on,
                "approver": names.get(approver) if approver else None,
            }
            for code, title, expires_on, approver in rows
        ]

    async def _active_control_ids(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> set[uuid.UUID]:
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        return await control_service.active_control_ids(session, tenant_id=tenant_id)

    # -- loading ---------------------------------------------------------------

    async def _load_register(
        self, session: AsyncSession, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> RiskRegister:
        row = await session.get(RiskRegister, register_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_REGISTER_GONE, detail=f"risk register {register_id}")
        return row

    async def _load(self, session: AsyncSession, tenant_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
        row = await session.get(Risk, risk_id, populate_existing=True)
        if row is None or row.tenant_id != tenant_id:
            raise NotFound(_RISK_GONE, detail=f"risk {risk_id}")
        return row

    async def _categories(
        self, session: AsyncSession, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> list[RiskCategory]:
        return list(
            (
                await session.execute(
                    select(RiskCategory)
                    .where(
                        RiskCategory.tenant_id == tenant_id,
                        RiskCategory.register_id == register_id,
                    )
                    .order_by(RiskCategory.position, RiskCategory.name)
                )
            ).scalars()
        )

    # -- history and audit -----------------------------------------------------

    async def _event(  # noqa: PLR0913, PLR0917 — one history row's fields
        self,
        session: AsyncSession,
        risk: Risk,
        actor: Actor,
        kind: str,
        from_value: str | None = None,
        to_value: str | None = None,
        note: str | None = None,
    ) -> None:
        await session.flush([risk])
        await session.refresh(risk, ["inherent_score", "residual_score"])
        session.add(
            RiskEvent(
                id=uuid7(),
                tenant_id=risk.tenant_id,
                risk_id=risk.id,
                kind=kind,
                from_value=from_value,
                to_value=to_value,
                note=note,
                inherent_score=risk.inherent_score,
                residual_score=risk.residual_score,
                actor_membership_id=_actor_id(actor),
            )
        )

    async def _record(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        risk: Risk,
        actor: Actor,
        action: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        await self._audit.record(
            session,
            action=action,  # type: ignore[arg-type]
            object_type="risk",
            object_id=risk.id,
            actor=actor,
            tenant_id=risk.tenant_id,
            before=before,
            after=after,
        )

    # =========================================================================
    # Registers
    # =========================================================================

    async def ensure_default_register(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor | None = None
    ) -> RiskRegister:
        """The workspace's default register, created on first use (§2.10)."""
        existing = (
            await session.execute(
                select(RiskRegister).where(
                    RiskRegister.tenant_id == tenant_id, RiskRegister.is_default.is_(True)
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        any_register = (
            await session.execute(
                select(RiskRegister)
                .where(RiskRegister.tenant_id == tenant_id)
                .order_by(RiskRegister.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        if any_register is not None:
            any_register.is_default = True
            await session.flush([any_register])
            return any_register
        return await self._new_register(
            session,
            tenant_id=tenant_id,
            actor=actor or System(),
            data=RegisterInput(name="Risk register", register_type="enterprise"),
            is_default=True,
        )

    async def _new_register(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        data: RegisterInput,
        is_default: bool,
    ) -> RiskRegister:
        name = _clean(data.name)
        if not name:
            raise InvalidInput("Give the register a name.", detail="register without a name")
        await self._check_register_name(session, tenant_id, name, None)
        self._check_type(data.register_type)
        likelihood = data.likelihood_levels or 5
        impact = data.impact_levels or 5
        scoring.validate_levels(likelihood, axis="likelihood")
        scoring.validate_levels(impact, axis="impact")
        formula = scoring.validate_formula(data.scoring_formula)
        top = scoring.max_score(formula, likelihood, impact)
        register = RiskRegister(
            id=uuid7(),
            tenant_id=tenant_id,
            name=name,
            register_type=data.register_type,
            description=_clean(data.description),
            owner_membership_id=data.owner_membership_id,
            is_default=is_default,
            status="active",
            likelihood_levels=likelihood,
            impact_levels=impact,
            likelihood_scale=(
                scoring.validate_scale(data.likelihood_scale, likelihood, axis="likelihood")
                if data.likelihood_scale
                else scoring.default_scale("likelihood", likelihood)
            ),
            impact_scale=(
                scoring.validate_scale(data.impact_scale, impact, axis="impact")
                if data.impact_scale
                else scoring.default_scale("impact", impact)
            ),
            severity_bands=(
                scoring.validate_bands(data.severity_bands, top)
                if data.severity_bands
                else scoring.default_bands(top)
            ),
            scoring_formula=formula,
            appetite={},
            review_cadence_days=data.review_cadence_days or 90,
            created_by_membership_id=_actor_id(actor),
        )
        session.add(register)
        await session.flush([register])
        for position, (category, children) in enumerate(scoring.DEFAULT_TAXONOMY):
            parent = RiskCategory(
                id=uuid7(),
                tenant_id=tenant_id,
                register_id=register.id,
                name=category,
                position=position,
            )
            session.add(parent)
            for child_position, child in enumerate(children):
                session.add(
                    RiskCategory(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        register_id=register.id,
                        parent_id=parent.id,
                        name=child,
                        position=child_position,
                    )
                )
        await session.flush()
        await self._audit.record(
            session,
            action="create",
            object_type="risk_register",
            object_id=register.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"name": register.name, "register_type": register.register_type},
        )
        return register

    def _check_type(self, register_type: str) -> None:
        if register_type not in REGISTER_TYPES:
            raise InvalidInput(
                "Choose a register type from the list.",
                detail=f"unknown register type {register_type!r}",
            )

    async def _check_register_name(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        exclude: uuid.UUID | None,
    ) -> None:
        stmt = select(RiskRegister.id).where(
            RiskRegister.tenant_id == tenant_id,
            func.lower(RiskRegister.name) == name.lower(),
        )
        if exclude is not None:
            stmt = stmt.where(RiskRegister.id != exclude)
        if (await session.execute(stmt)).first() is not None:
            raise Conflict(
                "A register with this name already exists. Choose another name.",
                detail=f"duplicate register name {name!r}",
            )

    async def list_registers(
        self, session: AsyncSession, *, tenant_id: uuid.UUID
    ) -> list[RegisterView]:
        await self.ensure_default_register(session, tenant_id=tenant_id)
        registers = list(
            (
                await session.execute(
                    select(RiskRegister)
                    .where(RiskRegister.tenant_id == tenant_id)
                    .order_by(RiskRegister.is_default.desc(), RiskRegister.name)
                )
            ).scalars()
        )
        names = await self._member_names(session, tenant_id)
        return [await self._register_view(session, r, names) for r in registers]

    async def get_register(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> RegisterView:
        register = await self._load_register(session, tenant_id, register_id)
        return await self._register_view(
            session, register, await self._member_names(session, tenant_id)
        )

    async def _register_view(
        self, session: AsyncSession, register: RiskRegister, names: dict[uuid.UUID, str]
    ) -> RegisterView:
        categories = await self._categories(session, register.tenant_id, register.id)
        usage: Counter[uuid.UUID] = Counter()
        rows = await session.execute(
            select(Risk.category_id, Risk.sub_category_id).where(
                Risk.tenant_id == register.tenant_id, Risk.register_id == register.id
            )
        )
        total = 0
        for category_id, sub_category_id in rows:
            total += 1
            usage[category_id] += 1
            if sub_category_id is not None:
                usage[sub_category_id] += 1
        children: dict[uuid.UUID, list[CategoryView]] = {}
        for row in categories:
            if row.parent_id is not None:
                children.setdefault(row.parent_id, []).append(
                    CategoryView(
                        row.id, row.name, row.position, row.archived_at is not None, usage[row.id]
                    )
                )
        tree = [
            CategoryView(
                row.id,
                row.name,
                row.position,
                row.archived_at is not None,
                usage[row.id],
                children.get(row.id, []),
            )
            for row in categories
            if row.parent_id is None
        ]
        return RegisterView(
            id=register.id,
            name=register.name,
            register_type=register.register_type,
            description=register.description,
            owner_membership_id=register.owner_membership_id,
            owner_name=names.get(register.owner_membership_id)
            if register.owner_membership_id
            else None,
            is_default=register.is_default,
            status=register.status,
            likelihood_levels=register.likelihood_levels,
            impact_levels=register.impact_levels,
            likelihood_scale=list(register.likelihood_scale),
            impact_scale=list(register.impact_scale),
            severity_bands=list(register.severity_bands),
            review_cadence_days=register.review_cadence_days,
            risk_count=total,
            categories=tree,
            created_at=register.created_at,
            scoring_formula=dict(register.scoring_formula or scoring.DEFAULT_FORMULA),
            appetite=dict(register.appetite or {}),
            max_score=scoring.max_score(
                register.scoring_formula or {}, register.likelihood_levels, register.impact_levels
            ),
        )

    async def create_register(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, actor: Actor, data: RegisterInput
    ) -> RegisterView:
        await self.ensure_default_register(session, tenant_id=tenant_id)
        register = await self._new_register(
            session, tenant_id=tenant_id, actor=actor, data=data, is_default=False
        )
        if data.is_default:
            await self._make_default(session, tenant_id, register)
        return await self.get_register(session, tenant_id=tenant_id, register_id=register.id)

    async def _make_default(
        self, session: AsyncSession, tenant_id: uuid.UUID, register: RiskRegister
    ) -> None:
        current = (
            await session.execute(
                select(RiskRegister).where(
                    RiskRegister.tenant_id == tenant_id,
                    RiskRegister.is_default.is_(True),
                    RiskRegister.id != register.id,
                )
            )
        ).scalars()
        for row in current:
            row.is_default = False
        await session.flush()
        register.is_default = True
        register.status = "active"
        await session.flush([register])

    async def update_register(  # noqa: PLR0912, PLR0915 — one branch per configurable part
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        register_id: uuid.UUID,
        data: RegisterInput,
    ) -> RegisterView:
        register = await self._load_register(session, tenant_id, register_id)
        before = AuditService.snapshot(register, fields=_REGISTER_SNAPSHOT)
        name = _clean(data.name)
        if not name:
            raise InvalidInput("Give the register a name.", detail="register without a name")
        await self._check_register_name(session, tenant_id, name, register.id)
        self._check_type(data.register_type)
        register.name = name
        register.register_type = data.register_type
        register.description = _clean(data.description)
        register.owner_membership_id = data.owner_membership_id

        likelihood = data.likelihood_levels or register.likelihood_levels
        impact = data.impact_levels or register.impact_levels
        scoring.validate_levels(likelihood, axis="likelihood")
        scoring.validate_levels(impact, axis="impact")
        if likelihood < register.likelihood_levels or impact < register.impact_levels:
            await self._guard_shrink(session, register, likelihood, impact)
        resized = (likelihood, impact) != (register.likelihood_levels, register.impact_levels)
        register.likelihood_levels = likelihood
        register.impact_levels = impact
        if data.likelihood_scale is not None:
            register.likelihood_scale = scoring.validate_scale(
                data.likelihood_scale, likelihood, axis="likelihood"
            )
        elif resized:
            register.likelihood_scale = scoring.default_scale("likelihood", likelihood)
        if data.impact_scale is not None:
            register.impact_scale = scoring.validate_scale(data.impact_scale, impact, axis="impact")
        elif resized:
            register.impact_scale = scoring.default_scale("impact", impact)
        formula = (
            scoring.validate_formula(data.scoring_formula)
            if data.scoring_formula is not None
            else dict(register.scoring_formula or scoring.DEFAULT_FORMULA)
        )
        reformula = formula != dict(register.scoring_formula or scoring.DEFAULT_FORMULA)
        register.scoring_formula = formula
        top = scoring.max_score(formula, likelihood, impact)
        if data.severity_bands is not None:
            register.severity_bands = scoring.validate_bands(data.severity_bands, top)
        elif resized or reformula:
            register.severity_bands = scoring.default_bands(top)
        if data.appetite is not None:
            register.appetite = scoring.validate_appetite(
                data.appetite,
                {
                    str(c.id)
                    for c in await self._categories(session, tenant_id, register.id)
                    if c.parent_id is None
                },
                top,
            )
        elif resized or reformula:
            register.appetite = {
                k: v for k, v in (register.appetite or {}).items() if v["tolerance"] <= top
            }

        if data.review_cadence_days is not None:
            if not 7 <= data.review_cadence_days <= 730:  # noqa: PLR2004 — the CHECK's bounds
                raise InvalidInput(
                    "Review cadence must be between 7 and 730 days.",
                    detail=f"cadence {data.review_cadence_days}",
                )
            register.review_cadence_days = data.review_cadence_days
        if data.status is not None and data.status != register.status:
            if data.status == "archived" and register.is_default:
                raise Conflict(
                    "The default register cannot be archived. "
                    "Make another register the default first.",
                    detail="archive default register",
                )
            register.status = data.status
        if data.is_default and not register.is_default:
            await self._make_default(session, tenant_id, register)
        await session.flush([register])
        if reformula:
            # The trigger re-reads the register's formula on every touched row.
            await session.execute(
                update(Risk)
                .where(Risk.tenant_id == tenant_id, Risk.register_id == register.id)
                .values(inherent_score=Risk.inherent_score)
                .execution_options(synchronize_session=False)
            )
        await self._audit.record(
            session,
            action="update",
            object_type="risk_register",
            object_id=register.id,
            actor=actor,
            tenant_id=tenant_id,
            before=before,
            after=AuditService.snapshot(register, fields=_REGISTER_SNAPSHOT),
        )
        return await self.get_register(session, tenant_id=tenant_id, register_id=register.id)

    async def _guard_shrink(
        self, session: AsyncSession, register: RiskRegister, likelihood: int, impact: int
    ) -> None:
        """Refuse a smaller matrix while any risk holds a level beyond it (§2.8)."""
        over = (
            await session.execute(
                select(func.count())
                .select_from(Risk)
                .where(
                    Risk.tenant_id == register.tenant_id,
                    Risk.register_id == register.id,
                    or_(
                        Risk.inherent_likelihood > likelihood,
                        Risk.residual_likelihood > likelihood,
                        Risk.inherent_impact > impact,
                        Risk.residual_impact > impact,
                    ),
                )
            )
        ).scalar_one()
        if over:
            raise Conflict(
                f"{over} risks are scored above the smaller scale. Rescore them first.",
                detail=f"{over} risks exceed {likelihood}x{impact}",
            )

    async def save_categories(  # noqa: PLR0912, PLR0915 — a tree diff
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        register_id: uuid.UUID,
        tree: Sequence[CategoryNode],
    ) -> RegisterView:
        """Save the taxonomy (§2.9).

        Rows are matched by id, then by name at the same level, so removing a
        category and adding it back revives the old row rather than orphaning the
        risks that use it. Unmatched rows are deleted when unused and archived
        (name kept) when a risk still points at them.
        """
        register = await self._load_register(session, tenant_id, register_id)
        rows = await self._categories(session, tenant_id, register.id)
        used: set[uuid.UUID] = set()
        for category_id, sub_category_id in await session.execute(
            select(Risk.category_id, Risk.sub_category_id).where(
                Risk.tenant_id == tenant_id, Risk.register_id == register.id
            )
        ):
            used.add(category_id)
            if sub_category_id is not None:
                used.add(sub_category_id)

        def names_of(nodes: Sequence[CategoryNode], what: str) -> list[str]:
            names = [(_clean(n.name) or "")[:80] for n in nodes]
            if any(not n for n in names):
                raise InvalidInput(f"Every {what} needs a name.", detail=f"blank {what} name")
            if len({n.lower() for n in names}) != len(names):
                raise InvalidInput(
                    f"Two {what} names are the same. Give each a different name.",
                    detail=f"duplicate {what} names",
                )
            return names

        if not tree:
            raise InvalidInput("Keep at least one category.", detail="taxonomy with no categories")
        top_names = names_of(tree, "category")

        claimed: dict[uuid.UUID, tuple[str, uuid.UUID | None, int]] = {}
        by_id = {row.id: row for row in rows}

        def claim(
            node: CategoryNode, name: str, parent: RiskCategory | None
        ) -> RiskCategory | None:
            parent_id = parent.id if parent else None
            candidates = [r for r in rows if r.parent_id == parent_id and r.id not in claimed]
            row = by_id.get(node.id) if node.id else None
            if row is None or row.id in claimed or row.parent_id != parent_id:
                row = next((r for r in candidates if r.name.lower() == name.lower()), None)
            return row

        plan: list[tuple[RiskCategory, str, uuid.UUID | None, int]] = []
        for position, (node, name) in enumerate(zip(tree, top_names, strict=True)):
            parent = claim(node, name, None)
            if parent is None:
                parent = RiskCategory(
                    id=uuid7(), tenant_id=tenant_id, register_id=register.id, name=name
                )
                session.add(parent)
                rows.append(parent)
            claimed[parent.id] = (name, None, position)
            plan.append((parent, name, None, position))
            for child_position, (child, child_name) in enumerate(
                zip(node.children, names_of(node.children, "subcategory"), strict=True)
            ):
                row = claim(child, child_name, parent)
                if row is None:
                    row = RiskCategory(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        register_id=register.id,
                        parent_id=parent.id,
                        name=child_name,
                    )
                    session.add(row)
                    rows.append(row)
                claimed[row.id] = (child_name, parent.id, child_position)
                plan.append((row, child_name, parent.id, child_position))

        # Park every existing claimed name first, so swaps and renames never meet
        # a stale sibling name in the unique index halfway through.
        for row, _name, _parent, _position in plan:
            if row in session.new:
                row.name = f"__new_{row.id}"
            else:
                row.name = f"__{row.id}"
        await session.flush()

        now = datetime.now(UTC)
        final_names = {(parent, name.lower()) for _row, name, parent, _p in plan}
        for row in list(by_id.values()):
            if row.id in claimed:
                continue
            if row.id in used:
                row.archived_at = row.archived_at or now
                if (row.parent_id, row.name.lower()) in final_names:
                    row.name = f"{row.name} (archived {str(row.id)[:4]})"
            else:
                await session.delete(row)
        await session.flush()

        for row, name, parent_id, position in plan:
            row.name = name
            row.parent_id = parent_id
            row.position = position
            row.archived_at = None
        await session.flush()

        await self._audit.record(
            session,
            action="update",
            object_type="risk_register",
            object_id=register.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"categories": top_names},
        )
        return await self.get_register(session, tenant_id=tenant_id, register_id=register.id)

    # =========================================================================
    # Risks
    # =========================================================================

    async def _next_code(self, session: AsyncSession, tenant_id: uuid.UUID) -> int:
        codes = (
            await session.execute(select(Risk.code).where(Risk.tenant_id == tenant_id))
        ).scalars()
        highest = 0
        for code in codes:
            match = _CODE_RE.match(code)
            if match:
                highest = max(highest, int(match.group(1)))
        return highest + 1

    async def _validate(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        register: RiskRegister,
        data: RiskInput,
    ) -> None:
        if not _clean(data.title):
            raise InvalidInput("Give the risk a title.", detail="risk without a title")
        if register.status != "active":
            raise Conflict(
                "This register is archived. Restore it before adding or changing risks.",
                detail="archived register",
            )
        category = await session.get(RiskCategory, data.category_id)
        if (
            category is None
            or category.tenant_id != tenant_id
            or category.register_id != register.id
            or category.parent_id is not None
        ):
            raise InvalidInput(
                "Choose a category from this register.", detail=f"category {data.category_id}"
            )
        if data.sub_category_id is not None:
            sub = await session.get(RiskCategory, data.sub_category_id)
            if sub is None or sub.tenant_id != tenant_id or sub.parent_id != category.id:
                raise InvalidInput(
                    "Choose a subcategory that belongs to the category.",
                    detail=f"sub category {data.sub_category_id} not under {category.id}",
                )
        if data.treatment is not None and data.treatment not in TREATMENTS:
            raise InvalidInput(
                "Choose a treatment from the list.", detail=f"treatment {data.treatment!r}"
            )
        for label, likelihood, impact in (
            ("inherent", data.inherent_likelihood, data.inherent_impact),
            ("residual", data.residual_likelihood, data.residual_impact),
        ):
            if (likelihood is None) != (impact is None):
                raise InvalidInput(
                    f"Score both {label} likelihood and impact, or neither.",
                    detail=f"partial {label} score",
                )
            if likelihood is not None and not 1 <= likelihood <= register.likelihood_levels:
                raise InvalidInput(
                    f"{label.capitalize()} likelihood must be between 1 and "
                    f"{register.likelihood_levels}.",
                    detail=f"{label} likelihood {likelihood}",
                )
            if impact is not None and not 1 <= impact <= register.impact_levels:
                raise InvalidInput(
                    f"{label.capitalize()} impact must be between 1 and {register.impact_levels}.",
                    detail=f"{label} impact {impact}",
                )
        if data.department_group_id is not None and data.department_group_id not in (
            await self._group_names(session, tenant_id)
        ):
            raise InvalidInput(
                "Choose a business unit from the list.",
                detail=f"group {data.department_group_id}",
            )
        if data.owner_membership_id is not None and data.owner_membership_id not in (
            await self._member_names(session, tenant_id)
        ):
            raise InvalidInput(
                "Choose an owner who is a member of this workspace.",
                detail=f"membership {data.owner_membership_id}",
            )

    def _assign(self, risk: Risk, data: RiskInput) -> None:
        risk.title = (_clean(data.title) or "")[:300]
        risk.description = (data.description or "").strip()
        risk.category_id = data.category_id
        risk.sub_category_id = data.sub_category_id
        risk.treatment = data.treatment
        risk.inherent_likelihood = data.inherent_likelihood
        risk.inherent_impact = data.inherent_impact
        risk.residual_likelihood = data.residual_likelihood
        risk.residual_impact = data.residual_impact
        risk.root_cause = _clean(data.root_cause)
        risk.consequences = _clean(data.consequences)
        risk.recommendations = _clean(data.recommendations)
        risk.treatment_plan = _clean(data.treatment_plan)
        risk.owner_membership_id = data.owner_membership_id
        risk.department_group_id = data.department_group_id
        risk.treatment_due_on = data.treatment_due_on

    async def custom_fields(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, include_archived: bool = False
    ) -> list[FieldDefinition]:
        return await custom_field_service.definitions(
            session, tenant_id=tenant_id, object_type="risk", include_archived=include_archived
        )

    async def clean_custom(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, values: dict[str, Any]
    ) -> dict[str, Any]:
        return await custom_field_service.clean(
            session, tenant_id=tenant_id, object_type="risk", values=values
        )

    async def save_custom_field(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        field_id: uuid.UUID | None,
        data: FieldInput,
    ) -> FieldDefinition:
        if field_id is None:
            view = await custom_field_service.create(
                session, tenant_id=tenant_id, object_type="risk", data=data
            )
        else:
            view = await custom_field_service.update(
                session, tenant_id=tenant_id, field_id=field_id, data=data
            )
        await self._audit.record(
            session,
            action="create" if field_id is None else "update",
            object_type="risk_custom_field",
            object_id=view.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"key": view.key, "label": view.label, "field_type": view.field_type},
        )
        await session.flush()
        return view

    async def set_custom_field_archived(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        field_id: uuid.UUID,
        archived: bool,
    ) -> FieldDefinition:
        view = await custom_field_service.set_archived(
            session, tenant_id=tenant_id, field_id=field_id, archived=archived
        )
        await self._audit.record(
            session,
            action="update",
            object_type="risk_custom_field",
            object_id=view.id,
            actor=actor,
            tenant_id=tenant_id,
            after={"key": view.key, "archived": archived},
        )
        await session.flush()
        return view

    async def create_risk(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        data: RiskInput,
        origin: str = "manual",
        template_id: uuid.UUID | None = None,
        origin_ref: uuid.UUID | None = None,
        code_number: int | None = None,
    ) -> Risk:
        """Create and return the row; callers render the view they need."""
        register = await self._load_register(session, tenant_id, data.register_id)
        await self._validate(session, tenant_id, register, data)
        if origin not in ORIGINS:
            raise InvalidInput("Unknown origin.", detail=f"origin {origin!r}")
        if data.status not in ("open", "in_treatment", "mitigated"):
            raise InvalidInput(
                "A new risk starts open, in treatment or mitigated.",
                detail=f"create with status {data.status!r}",
            )
        number = code_number or await self._next_code(session, tenant_id)
        risk = Risk(
            id=uuid7(),
            tenant_id=tenant_id,
            register_id=register.id,
            code=f"{_CODE_PREFIX}{number:04d}",
            status=data.status,
            origin=origin,
            template_id=template_id,
            origin_ref=origin_ref,
            next_review_on=data.next_review_on
            or (datetime.now(UTC).date() + timedelta(days=register.review_cadence_days)),
            created_by_membership_id=_actor_id(actor),
        )
        self._assign(risk, data)
        if data.custom_fields or origin in ("manual", "import"):
            risk.custom_fields = await custom_field_service.clean(
                session, tenant_id=tenant_id, object_type="risk", values=data.custom_fields
            )
        session.add(risk)
        await session.flush([risk])
        kind = {"library": "adopted", "import": "imported", "vendor_finding": "promoted"}.get(
            origin, "created"
        )
        await self._event(session, risk, actor, kind, None, risk.code)
        await self._record(
            session,
            risk,
            actor,
            "create",
            None,
            AuditService.snapshot(risk, fields=_SNAPSHOT_FIELDS),
        )
        if data.asset_ids:
            await self._sync_assets(session, risk, actor, data.asset_ids)
        return risk

    async def update_risk(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        data: RiskInput,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        if data.register_id != risk.register_id:
            raise InvalidInput(
                "A risk stays in its register.", detail="moving a risk between registers"
            )
        register = await self._load_register(session, tenant_id, risk.register_id)
        await self._validate(session, tenant_id, register, data)
        before = AuditService.snapshot(risk, fields=_SNAPSHOT_FIELDS)
        old_scores = (
            _pair(risk.inherent_likelihood, risk.inherent_impact),
            _pair(risk.residual_likelihood, risk.residual_impact),
        )
        old_treatment = risk.treatment
        old_owner = risk.owner_membership_id
        if data.status != risk.status:
            if risk.status in ("accepted", "closed") or data.status in ("accepted", "closed"):
                raise InvalidInput(
                    "Use close, reopen or acceptance to change this status.",
                    detail=f"status {risk.status} -> {data.status} through edit",
                )
            scoring.check_transition(risk.status, data.status)
            await self._event(session, risk, actor, "status", risk.status, data.status)
            risk.status = data.status
        self._assign(risk, data)
        if data.custom_fields is not None:
            risk.custom_fields = await custom_field_service.clean(
                session,
                tenant_id=tenant_id,
                object_type="risk",
                values=data.custom_fields,
                previous=dict(risk.custom_fields or {}),
            )
        if data.next_review_on is not None:
            risk.next_review_on = data.next_review_on
        new_scores = (
            _pair(risk.inherent_likelihood, risk.inherent_impact),
            _pair(risk.residual_likelihood, risk.residual_impact),
        )
        if new_scores != old_scores:
            await self._event(
                session,
                risk,
                actor,
                "scored",
                " / ".join(s or "unscored" for s in old_scores),
                " / ".join(s or "unscored" for s in new_scores),
            )
        if risk.treatment != old_treatment:
            await self._event(session, risk, actor, "treatment", old_treatment, risk.treatment)
        if risk.owner_membership_id != old_owner:
            names = await self._member_names(session, tenant_id)
            await self._event(
                session,
                risk,
                actor,
                "owner",
                names.get(old_owner) if old_owner else None,
                names.get(risk.owner_membership_id) if risk.owner_membership_id else None,
            )
        after = AuditService.snapshot(risk, fields=_SNAPSHOT_FIELDS)
        if after != before:
            await self._event(session, risk, actor, "updated")
            await self._record(session, risk, actor, "update", before, after)
        if data.asset_ids is not None:
            await self._sync_assets(session, risk, actor, data.asset_ids)
        await session.flush()
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def transition(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        status: str,
        note: str | None = None,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        if status not in RISK_STATUSES or status == "accepted":
            raise InvalidInput(
                "Accepting a risk goes through an acceptance request.",
                detail=f"manual transition to {status!r}",
            )
        scoring.check_transition(risk.status, status)
        if status == risk.status:
            return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)
        reason = _clean(note)
        before = {"status": risk.status}
        if status == "closed":
            if not reason:
                raise InvalidInput(
                    "Say why the risk is closed. The reason stays on the record.",
                    detail="close without justification",
                )
            risk.closure_justification = reason
            risk.closed_at = datetime.now(UTC)
            risk.closed_by_membership_id = _actor_id(actor)
            await self._settle_acceptances(session, risk, actor, "revoked", "Risk closed")
        if risk.status == "closed":
            if not reason:
                raise InvalidInput("Say why the risk is reopened.", detail="reopen without a note")
            risk.closed_at = None
            risk.closed_by_membership_id = None
        await self._event(session, risk, actor, "status", risk.status, status, reason)
        risk.status = status
        await session.flush([risk])
        await self._record(
            session, risk, actor, "transition", before, {"status": status, "note": reason}
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def mark_reviewed(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        note: str | None,
        next_review_on: date | None,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        register = await self._load_register(session, tenant_id, risk.register_id)
        today = datetime.now(UTC).date()
        target = next_review_on or today + timedelta(days=register.review_cadence_days)
        if target <= today:
            raise InvalidInput("Set the next review in the future.", detail=f"next review {target}")
        before = {
            "next_review_on": risk.next_review_on.isoformat() if risk.next_review_on else None
        }
        risk.last_reviewed_at = datetime.now(UTC)
        risk.next_review_on = target
        await self._event(
            session,
            risk,
            actor,
            "reviewed",
            before["next_review_on"],
            target.isoformat(),
            _clean(note),
        )
        await self._record(
            session, risk, actor, "update", before, {"next_review_on": target.isoformat()}
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    # -- reads -----------------------------------------------------------------

    async def _control_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID, risk_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not risk_ids:
            return {}
        active = await self._active_control_ids(session, tenant_id)
        rows = await session.execute(
            select(RiskControlMap.risk_id, RiskControlMap.control_id).where(
                RiskControlMap.tenant_id == tenant_id,
                RiskControlMap.risk_id.in_(list(risk_ids)),
            )
        )
        counts: Counter[uuid.UUID] = Counter()
        for risk_id, control_id in rows:
            if control_id in active:
                counts[risk_id] += 1
        return dict(counts)

    async def _acceptance_flags(
        self, session: AsyncSession, tenant_id: uuid.UUID, risk_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """``pending`` or ``expiring`` per risk, for the attention list."""
        if not risk_ids:
            return {}
        horizon = datetime.now(UTC).date() + timedelta(days=_EXPIRY_WARNING_DAYS)
        rows = await session.execute(
            select(RiskAcceptance.risk_id, RiskAcceptance.status, RiskAcceptance.expires_on).where(
                RiskAcceptance.tenant_id == tenant_id,
                RiskAcceptance.risk_id.in_(list(risk_ids)),
                RiskAcceptance.status.in_(("pending", "active")),
            )
        )
        out: dict[uuid.UUID, str] = {}
        for risk_id, status, expires_on in rows:
            if status == "pending":
                out[risk_id] = "acceptance_pending"
            elif expires_on <= horizon:
                out[risk_id] = "acceptance_expiring"
        return out

    def _attention(
        self,
        risk: Risk,
        control_count: int,
        acceptance_flag: str | None,
        today: date,
    ) -> list[str]:
        live = risk.status not in ("closed",)
        flags: list[str] = []
        if live and risk.status != "accepted" and control_count == 0:
            flags.append("no_controls")
        if live and risk.next_review_on is not None and risk.next_review_on < today:
            flags.append("review_overdue")
        if (
            risk.status in ("open", "in_treatment")
            and risk.treatment_due_on is not None
            and risk.treatment_due_on < today
        ):
            flags.append("treatment_overdue")
        if live and risk.inherent_score is None:
            flags.append("unscored")
        if live and risk.owner_membership_id is None:
            flags.append("unowned")
        if acceptance_flag:
            flags.append(acceptance_flag)
        return flags

    def _view(  # noqa: PLR0913, PLR0917
        self,
        risk: Risk,
        register: RiskRegister,
        categories: dict[uuid.UUID, str],
        names: dict[uuid.UUID, str],
        groups: dict[uuid.UUID, str],
        control_count: int,
        acceptance_flag: str | None,
        today: date,
    ) -> RiskView:
        bands = register.severity_bands
        return RiskView(
            id=risk.id,
            register_id=risk.register_id,
            code=risk.code,
            title=risk.title,
            description=risk.description,
            category_id=risk.category_id,
            category_name=categories.get(risk.category_id, ""),
            sub_category_id=risk.sub_category_id,
            sub_category_name=categories.get(risk.sub_category_id)
            if risk.sub_category_id
            else None,
            status=risk.status,
            treatment=risk.treatment,
            inherent_likelihood=risk.inherent_likelihood,
            inherent_impact=risk.inherent_impact,
            inherent_score=risk.inherent_score,
            inherent_band=scoring.band_for(bands, risk.inherent_score),
            residual_likelihood=risk.residual_likelihood,
            residual_impact=risk.residual_impact,
            residual_score=risk.residual_score,
            residual_band=scoring.band_for(bands, risk.residual_score),
            owner=(
                Person(
                    risk.owner_membership_id, names.get(risk.owner_membership_id, "Former member")
                )
                if risk.owner_membership_id
                else None
            ),
            department_group_id=risk.department_group_id,
            department_name=groups.get(risk.department_group_id)
            if risk.department_group_id
            else None,
            treatment_due_on=risk.treatment_due_on,
            next_review_on=risk.next_review_on,
            last_reviewed_at=risk.last_reviewed_at,
            origin=risk.origin,
            control_count=control_count,
            attention=self._attention(risk, control_count, acceptance_flag, today),
            appetite_status=scoring.appetite_status(
                (register.appetite or {}).get(str(risk.category_id)),
                risk.residual_score or risk.inherent_score,
            ),
            custom_fields=dict(risk.custom_fields or {}),
            created_at=risk.created_at,
            updated_at=risk.updated_at,
        )

    async def _category_names(
        self, session: AsyncSession, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        return {row.id: row.name for row in await self._categories(session, tenant_id, register_id)}

    def _filtered(  # noqa: PLR0912, PLR0915 — one clause per documented filter
        self,
        tenant_id: uuid.UUID,
        register: RiskRegister,
        filters: RiskFilters,
        me: uuid.UUID | None,
        active_controls: set[uuid.UUID],
    ) -> Select[tuple[Risk]]:
        stmt = select(Risk).where(Risk.tenant_id == tenant_id, Risk.register_id == register.id)
        today = datetime.now(UTC).date()
        if filters.search:
            term = f"%{filters.search.strip()}%"
            stmt = stmt.where(
                or_(Risk.title.ilike(term), Risk.code.ilike(term), Risk.description.ilike(term))
            )
        if filters.statuses:
            stmt = stmt.where(Risk.status.in_(list(filters.statuses)))
        elif not filters.include_closed:
            stmt = stmt.where(Risk.status != "closed")
        if filters.category_ids:
            stmt = stmt.where(
                or_(
                    Risk.category_id.in_(list(filters.category_ids)),
                    Risk.sub_category_id.in_(list(filters.category_ids)),
                )
            )
        if filters.treatments:
            wanted = [t for t in filters.treatments if t != "undecided"]
            clauses = [Risk.treatment.in_(wanted)] if wanted else []
            if "undecided" in filters.treatments:
                clauses.append(Risk.treatment.is_(None))
            stmt = stmt.where(or_(*clauses))
        if filters.owner == "me" and me is not None:
            stmt = stmt.where(Risk.owner_membership_id == me)
        elif filters.owner == "unassigned":
            stmt = stmt.where(Risk.owner_membership_id.is_(None))
        elif filters.owner:
            with contextlib.suppress(ValueError):
                stmt = stmt.where(Risk.owner_membership_id == uuid.UUID(filters.owner))
        if filters.department_ids:
            stmt = stmt.where(Risk.department_group_id.in_(list(filters.department_ids)))
        by_key: dict[str, list[str]] = {}
        for key, value in filters.custom:
            by_key.setdefault(key, []).append(value)
        for key, values in by_key.items():
            stmt = stmt.where(Risk.custom_fields[key].astext.in_(values))
        if filters.bands:
            ranges = scoring.band_ranges(
                register.severity_bands,
                scoring.max_score(
                    register.scoring_formula or {},
                    register.likelihood_levels,
                    register.impact_levels,
                ),
            )
            effective = func.coalesce(Risk.residual_score, Risk.inherent_score)
            clauses = [effective.between(*ranges[band]) for band in filters.bands if band in ranges]
            if "unscored" in filters.bands:
                clauses.append(Risk.inherent_score.is_(None))
            if clauses:
                stmt = stmt.where(or_(*clauses))
        if filters.cell:
            parts = filters.cell.split(":")
            if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():  # noqa: PLR2004
                likelihood, impact = int(parts[1]), int(parts[2])
                if parts[0] == "residual":
                    stmt = stmt.where(
                        Risk.residual_likelihood == likelihood, Risk.residual_impact == impact
                    )
                else:
                    stmt = stmt.where(
                        Risk.inherent_likelihood == likelihood, Risk.inherent_impact == impact
                    )
                stmt = stmt.where(Risk.status != "closed")
        live = Risk.status != "closed"
        for flag in filters.attention:
            if flag == "no_controls":
                has_control = exists().where(
                    RiskControlMap.tenant_id == tenant_id,
                    RiskControlMap.risk_id == Risk.id,
                    RiskControlMap.control_id.in_(list(active_controls) or [uuid.UUID(int=0)]),
                )
                stmt = stmt.where(live, Risk.status != "accepted", ~has_control)
            elif flag == "review_overdue":
                stmt = stmt.where(live, Risk.next_review_on < today)
            elif flag == "treatment_overdue":
                stmt = stmt.where(
                    Risk.status.in_(("open", "in_treatment")), Risk.treatment_due_on < today
                )
            elif flag == "unscored":
                stmt = stmt.where(live, Risk.inherent_score.is_(None))
            elif flag == "unowned":
                stmt = stmt.where(live, Risk.owner_membership_id.is_(None))
            elif flag in ("acceptance_pending", "acceptance_expiring"):
                condition = [
                    RiskAcceptance.tenant_id == tenant_id,
                    RiskAcceptance.risk_id == Risk.id,
                ]
                if flag == "acceptance_pending":
                    condition.append(RiskAcceptance.status == "pending")
                else:
                    condition += [
                        RiskAcceptance.status == "active",
                        RiskAcceptance.expires_on <= today + timedelta(days=_EXPIRY_WARNING_DAYS),
                    ]
                stmt = stmt.where(exists().where(and_(*condition)))
        return stmt

    async def list_risks(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        filters: RiskFilters,
        me: uuid.UUID | None = None,
        sort: str | None = None,
        direction: str = "desc",
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[RiskView], int]:
        register = await self._load_register(session, tenant_id, filters.register_id)
        active = await self._active_control_ids(session, tenant_id)
        stmt = self._filtered(tenant_id, register, filters, me, active)
        total = (
            await session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        effective = func.coalesce(Risk.residual_score, Risk.inherent_score)
        order: Any
        column = {
            "code": Risk.code,
            "title": func.lower(Risk.title),
            "inherent": Risk.inherent_score,
            "residual": effective,
            "status": Risk.status,
            "next_review": Risk.next_review_on,
            "updated": Risk.updated_at,
        }.get(sort or "")
        if column is None:
            # The register's natural order: worst exposure first, then newest.
            stmt = stmt.order_by(effective.desc().nulls_last(), Risk.code.desc())
        else:
            order = column.asc().nulls_last() if direction == "asc" else column.desc().nulls_last()
            stmt = stmt.order_by(order, Risk.code.desc())
        size = max(1, min(page_size, _MAX_PAGE_SIZE))
        stmt = stmt.offset((max(page, 1) - 1) * size).limit(size)
        risks = list((await session.execute(stmt)).scalars())
        return await self._views(session, tenant_id, register, risks), total

    async def _views(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        register: RiskRegister,
        risks: Sequence[Risk],
    ) -> list[RiskView]:
        ids = [r.id for r in risks]
        categories = await self._category_names(session, tenant_id, register.id)
        names = await self._member_names(session, tenant_id)
        groups = await self._group_names(session, tenant_id)
        counts = await self._control_counts(session, tenant_id, ids)
        flags = await self._acceptance_flags(session, tenant_id, ids)
        today = datetime.now(UTC).date()
        return [
            self._view(
                r, register, categories, names, groups, counts.get(r.id, 0), flags.get(r.id), today
            )
            for r in risks
        ]

    async def all_risks(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, filters: RiskFilters
    ) -> list[RiskView]:
        """Every matching risk, unpaged, for export."""
        items, _ = await self.list_risks(
            session, tenant_id=tenant_id, filters=filters, page=1, page_size=_MAX_PAGE_SIZE
        )
        if len(items) < _MAX_PAGE_SIZE:
            return items
        register = await self._load_register(session, tenant_id, filters.register_id)
        active = await self._active_control_ids(session, tenant_id)
        stmt = self._filtered(tenant_id, register, filters, None, active).order_by(Risk.code)
        risks = list((await session.execute(stmt)).scalars())
        return await self._views(session, tenant_id, register, risks)

    async def get_risk(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> RiskDetailView:
        # Every mutating method renders through here, and the load below uses
        # populate_existing: without this flush a change still pending in the
        # session (autoflush is off) is silently overwritten by the stored row.
        await session.flush()
        risk = await self._load(session, tenant_id, risk_id)
        await session.refresh(risk)
        register = await self._load_register(session, tenant_id, risk.register_id)
        names = await self._member_names(session, tenant_id)
        base = (await self._views(session, tenant_id, register, [risk]))[0]
        template_code = None
        if risk.template_id is not None:
            template = await session.get(RiskTemplate, risk.template_id)
            template_code = template.code if template else None
        allowed = list(scoring.STATUS_TRANSITIONS.get(risk.status, ()))
        return RiskDetailView(
            **{f: getattr(base, f) for f in RiskView.__dataclass_fields__},
            root_cause=risk.root_cause,
            consequences=risk.consequences,
            recommendations=risk.recommendations,
            treatment_plan=risk.treatment_plan,
            closure_justification=risk.closure_justification,
            closed_at=risk.closed_at,
            template_code=template_code,
            origin_ref=risk.origin_ref,
            created_by_name=(
                names.get(risk.created_by_membership_id) if risk.created_by_membership_id else None
            ),
            allowed_statuses=allowed,
            controls=await self._controls_of(session, tenant_id, risk.id),
            links=await self._links_of(session, tenant_id, risk.id),
            actions=await self._actions_of(session, tenant_id, risk.id),
            acceptances=await self._acceptances_of(session, tenant_id, risk.id, names),
            history=await self._history_of(session, tenant_id, risk.id, names),
        )

    async def _history_of(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        risk_id: uuid.UUID,
        names: dict[uuid.UUID, str],
    ) -> list[EventView]:
        rows = (
            await session.execute(
                select(RiskEvent)
                .where(RiskEvent.tenant_id == tenant_id, RiskEvent.risk_id == risk_id)
                .order_by(RiskEvent.created_at.desc(), RiskEvent.id.desc())
                .limit(200)
            )
        ).scalars()
        return [
            EventView(
                id=e.id,
                kind=e.kind,
                from_value=e.from_value,
                to_value=e.to_value,
                note=e.note,
                inherent_score=e.inherent_score,
                residual_score=e.residual_score,
                actor_name=names.get(e.actor_membership_id) if e.actor_membership_id else None,
                created_at=e.created_at,
            )
            for e in rows
        ]

    async def refs(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, search: str | None, limit: int = 20
    ) -> list[RiskRef]:
        """A light picker across every register, for other modules linking to risks."""
        stmt = (
            select(Risk, RiskRegister)
            .join(RiskRegister, RiskRegister.id == Risk.register_id)
            .where(Risk.tenant_id == tenant_id, Risk.status != "closed")
        )
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(or_(Risk.title.ilike(term), Risk.code.ilike(term)))
        stmt = stmt.order_by(Risk.code.desc()).limit(max(1, min(limit, 50)))
        return [
            RiskRef(
                id=r.id,
                code=r.code,
                title=r.title,
                status=r.status,
                band=scoring.band_for(reg.severity_bands, r.residual_score or r.inherent_score),
                register_name=reg.name,
            )
            for r, reg in (await session.execute(stmt)).all()
        ]

    async def get_ref(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> RiskRef:
        """One risk as another module shows it in a list of linked records."""
        row = (
            await session.execute(
                select(Risk, RiskRegister)
                .join(RiskRegister, RiskRegister.id == Risk.register_id)
                .where(Risk.tenant_id == tenant_id, Risk.id == risk_id)
            )
        ).first()
        if row is None:
            raise NotFound(_RISK_GONE, detail=f"risk {risk_id}")
        risk, register = row
        return RiskRef(
            id=risk.id,
            code=risk.code,
            title=risk.title,
            status=risk.status,
            band=scoring.band_for(
                register.severity_bands, risk.residual_score or risk.inherent_score
            ),
            register_name=register.name,
        )

    # =========================================================================
    # Controls
    # =========================================================================

    async def _controls_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> list[ControlRefView]:
        linked = set(
            (
                await session.execute(
                    select(RiskControlMap.control_id).where(
                        RiskControlMap.tenant_id == tenant_id, RiskControlMap.risk_id == risk_id
                    )
                )
            ).scalars()
        )
        if not linked:
            return []
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        controls = await control_service.list_controls(
            session, tenant_id=tenant_id, include_disabled=True
        )
        return sorted(
            (
                ControlRefView(
                    id=c.id,
                    code=c.code,
                    name=c.name,
                    status=c.status,
                    category=c.category,
                    disabled=c.disabled_at is not None,
                )
                for c in controls
                if c.id in linked
            ),
            key=lambda c: c.code,
        )

    async def link_controls(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        control_ids: Sequence[uuid.UUID],
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        known = {
            c.id: c
            for c in await control_service.list_controls(
                session, tenant_id=tenant_id, include_disabled=False
            )
        }
        await self._add_controls(
            session, risk, actor, control_ids, known_codes={k: v.code for k, v in known.items()}
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def _add_controls(
        self,
        session: AsyncSession,
        risk: Risk,
        actor: Actor,
        control_ids: Iterable[uuid.UUID],
        *,
        known_codes: dict[uuid.UUID, str],
    ) -> int:
        existing = set(
            (
                await session.execute(
                    select(RiskControlMap.control_id).where(
                        RiskControlMap.tenant_id == risk.tenant_id,
                        RiskControlMap.risk_id == risk.id,
                    )
                )
            ).scalars()
        )
        added = 0
        for control_id in dict.fromkeys(control_ids):
            if control_id not in known_codes:
                raise InvalidInput(
                    "Choose active controls from this workspace.",
                    detail=f"control {control_id} unknown or disabled",
                )
            if control_id in existing:
                continue
            session.add(
                RiskControlMap(
                    id=uuid7(),
                    tenant_id=risk.tenant_id,
                    risk_id=risk.id,
                    control_id=control_id,
                    created_by_membership_id=_actor_id(actor),
                )
            )
            await self._event(session, risk, actor, "control_linked", None, known_codes[control_id])
            added += 1
        if added:
            await session.flush()
            await self._record(session, risk, actor, "update", None, {"controls_linked": added})
        return added

    async def unlink_control(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        control_id: uuid.UUID,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        row = (
            await session.execute(
                select(RiskControlMap).where(
                    RiskControlMap.tenant_id == tenant_id,
                    RiskControlMap.risk_id == risk.id,
                    RiskControlMap.control_id == control_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFound(
                "That control is not linked to this risk.", detail=f"control {control_id}"
            )
        codes = {c.id: c.code for c in await self._controls_of(session, tenant_id, risk.id)}
        await session.delete(row)
        await self._event(session, risk, actor, "control_unlinked", codes.get(control_id), None)
        await self._record(session, risk, actor, "update", {"control": str(control_id)}, None)
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def control_ids_for_risk(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """The controls that mitigate one risk, oldest link first. The trace reads the
        pair through here; it never opens ``risk_control_map`` itself."""
        rows = await session.execute(
            select(RiskControlMap.control_id)
            .where(RiskControlMap.tenant_id == tenant_id, RiskControlMap.risk_id == risk_id)
            .order_by(RiskControlMap.created_at, RiskControlMap.id)
        )
        return list(rows.scalars())

    async def risk_ids_for_control(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, control_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """The risks one control mitigates, oldest link first: the control page's linked
        records and the trace read them through here."""
        rows = await session.execute(
            select(RiskControlMap.risk_id)
            .where(RiskControlMap.tenant_id == tenant_id, RiskControlMap.control_id == control_id)
            .order_by(RiskControlMap.created_at, RiskControlMap.id)
        )
        return list(rows.scalars())

    # =========================================================================
    # Links and treatment actions
    # =========================================================================

    async def _resolve(  # noqa: PLR0911 — one branch per linkable module
        self, session: AsyncSession, tenant_id: uuid.UUID, target_type: str, target_id: uuid.UUID
    ) -> tuple[str, str, str, str | None] | None:
        """``(code, title, status, detail)`` of a linked record, or None if gone."""
        try:
            if target_type == "asset":
                from verity.modules.assets.service import asset_service  # noqa: PLC0415

                asset = await asset_service.get_asset(
                    session, tenant_id=tenant_id, asset_id=target_id
                )
                return asset.hostname or "", asset.name, asset.status, asset.asset_type
            if target_type == "vulnerability":
                from verity.modules.vulnerabilities.service import (  # noqa: PLC0415
                    vulnerability_service,
                )

                vuln = await vulnerability_service.get_instance(
                    session, tenant_id=tenant_id, instance_id=target_id
                )
                return vuln.cve_id or "", vuln.title, vuln.state, vuln.severity
            if target_type == "evidence":
                from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

                evidence = await evidence_service.get(
                    session, tenant_id=tenant_id, evidence_id=target_id
                )
                return "", evidence.title, evidence.freshness, evidence.evidence_type
            if target_type == "task":
                from verity.modules.tasks.service import task_service  # noqa: PLC0415

                task = await task_service.get_task(session, tenant_id=tenant_id, task_id=target_id)
                return task.code, task.title, task.status, task.task_kind
            if target_type == "vendor":
                from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

                vendor = await vendor_service.get_ref(
                    session, tenant_id=tenant_id, vendor_id=target_id
                )
                return "", vendor.name, vendor.lifecycle_status, vendor.tier
            if target_type == "document":
                from verity.modules.documents.service import document_service  # noqa: PLC0415

                doc = await document_service.get_document(
                    session, tenant_id=tenant_id, document_id=target_id
                )
                return doc.code, doc.title, doc.lifecycle, doc.doc_type
        except NotFound:
            return None
        return None

    async def _edges(
        self, session: AsyncSession, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> list[Any]:
        from verity.modules.links.service import link_service  # noqa: PLC0415

        return await link_service.for_object(
            session, tenant_id=tenant_id, obj_type="risk", obj_id=risk_id
        )

    async def _links_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> list[LinkedRecordView]:
        out: list[LinkedRecordView] = []
        for edge in await self._edges(session, tenant_id, risk_id):
            if edge.other_type not in LINKABLE_TYPES:
                continue
            if edge.other_type == "task" and edge.relation == "remediates":
                continue  # a treatment action, listed under actions
            resolved = await self._resolve(session, tenant_id, edge.other_type, edge.other_id)
            if resolved is None:
                continue
            code, title, status, detail = resolved
            out.append(
                LinkedRecordView(
                    link_id=edge.link_id,
                    target_type=edge.other_type,
                    target_id=edge.other_id,
                    relation=edge.relation,
                    code=code,
                    title=title,
                    status=status,
                    detail=detail,
                )
            )
        out.sort(key=lambda r: (r.target_type, r.title.lower()))
        return out

    async def _actions_of(
        self, session: AsyncSession, tenant_id: uuid.UUID, risk_id: uuid.UUID
    ) -> list[ActionView]:
        from verity.modules.tasks.service import task_service  # noqa: PLC0415

        out: list[ActionView] = []
        for edge in await self._edges(session, tenant_id, risk_id):
            if edge.other_type != "task" or edge.relation != "remediates":
                continue
            try:
                task = await task_service.get_task(
                    session, tenant_id=tenant_id, task_id=edge.other_id
                )
            except NotFound:
                continue
            out.append(
                ActionView(
                    link_id=edge.link_id,
                    task_id=task.id,
                    code=task.code,
                    title=task.title,
                    status=task.status,
                    priority=task.priority,
                    owner_name=task.owner.name if task.owner else None,
                    due_at=task.due_at,
                )
            )
        out.sort(
            key=lambda a: (
                a.status in ("closed", "cancelled"),
                a.due_at or datetime.max.replace(tzinfo=UTC),
            )
        )
        return out

    async def link_record(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        target_type: str,
        target_id: uuid.UUID,
        relation: str = "relates_to",
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        await self._link(session, risk, actor, target_type, target_id, relation)
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def _link(  # noqa: PLR0913, PLR0917
        self,
        session: AsyncSession,
        risk: Risk,
        actor: Actor,
        target_type: str,
        target_id: uuid.UUID,
        relation: str = "relates_to",
    ) -> None:
        if target_type not in LINKABLE_TYPES:
            raise InvalidInput(
                "That is not something a risk can link to.", detail=f"link type {target_type!r}"
            )
        resolved = await self._resolve(session, risk.tenant_id, target_type, target_id)
        if resolved is None:
            raise NotFound("That record no longer exists.", detail=f"{target_type} {target_id}")
        from verity.modules.links.service import link_service  # noqa: PLC0415

        await link_service.create(
            session,
            tenant_id=risk.tenant_id,
            from_type="risk",
            from_id=risk.id,
            to_type=target_type,
            to_id=target_id,
            relation=relation,
            created_by_membership_id=_actor_id(actor),
        )
        label = " ".join(p for p in (resolved[0], resolved[1]) if p)
        await self._event(session, risk, actor, "linked", target_type, label)
        await self._record(
            session, risk, actor, "update", None, {"linked": f"{target_type}:{target_id}"}
        )

    async def unlink_record(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        link_id: uuid.UUID,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        edge = next(
            (e for e in await self._edges(session, tenant_id, risk.id) if e.link_id == link_id),
            None,
        )
        if edge is None:
            raise NotFound("This link no longer exists.", detail=f"link {link_id}")
        resolved = await self._resolve(session, tenant_id, edge.other_type, edge.other_id)
        from verity.modules.links.service import link_service  # noqa: PLC0415

        await link_service.delete(session, tenant_id=tenant_id, link_id=link_id)
        label = " ".join(p for p in (resolved[0], resolved[1]) if p) if resolved else None
        await self._event(session, risk, actor, "unlinked", edge.other_type, label)
        await self._record(session, risk, actor, "update", {"link": str(link_id)}, None)
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def _sync_assets(
        self, session: AsyncSession, risk: Risk, actor: Actor, asset_ids: Sequence[uuid.UUID]
    ) -> None:
        """Make the risk's asset links exactly ``asset_ids`` (the form's picker)."""
        from verity.modules.links.service import link_service  # noqa: PLC0415

        current = {
            e.other_id: e
            for e in await self._edges(session, risk.tenant_id, risk.id)
            if e.other_type == "asset"
        }
        wanted = set(asset_ids)
        for asset_id in wanted - set(current):
            await self._link(session, risk, actor, "asset", asset_id)
        for asset_id, edge in current.items():
            if asset_id not in wanted:
                await link_service.delete(session, tenant_id=risk.tenant_id, link_id=edge.link_id)
                await self._event(session, risk, actor, "unlinked", "asset", None)

    async def add_action(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        title: str,
        description: str | None,
        priority: str,
        owner_membership_id: uuid.UUID | None,
        due_on: date | None,
    ) -> RiskDetailView:
        """A treatment action is a task that remediates the risk (R9)."""
        risk = await self._load(session, tenant_id, risk_id)
        if risk.status == "closed":
            raise Conflict("Reopen the risk before adding actions.", detail="action on closed risk")
        if not _clean(title):
            raise InvalidInput("Give the action a title.", detail="action without title")
        register = await self._load_register(session, tenant_id, risk.register_id)
        from verity.modules.links.service import link_service  # noqa: PLC0415
        from verity.modules.tasks.service import task_service  # noqa: PLC0415

        task = await task_service.create_task(
            session,
            tenant_id=tenant_id,
            actor=actor,
            task_kind="task",
            title=(_clean(title) or "")[:200],
            description=_clean(description) or f"Treatment action for {risk.code} {risk.title}",
            priority=priority,
            category=_ACTION_CATEGORY.get(register.register_type, "security"),
            owner_membership_id=owner_membership_id or risk.owner_membership_id,
            due_at=datetime.combine(due_on, datetime.min.time(), tzinfo=UTC) if due_on else None,
            raised_from_type="risk",
        )
        await link_service.create(
            session,
            tenant_id=tenant_id,
            from_type="task",
            from_id=task.id,
            to_type="risk",
            to_id=risk.id,
            relation="remediates",
            created_by_membership_id=_actor_id(actor),
        )
        await self._event(session, risk, actor, "action_added", None, f"{task.code} {task.title}")
        if risk.status == "open":
            await self._event(
                session, risk, actor, "status", "open", "in_treatment", "Action added"
            )
            risk.status = "in_treatment"
        if risk.treatment is None:
            risk.treatment = "mitigate"
        await self._record(session, risk, actor, "update", None, {"action": task.code})
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    # =========================================================================
    # Acceptances
    # =========================================================================

    async def _acceptances_of(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        risk_id: uuid.UUID,
        names: dict[uuid.UUID, str],
    ) -> list[AcceptanceView]:
        rows = (
            await session.execute(
                select(RiskAcceptance)
                .where(RiskAcceptance.tenant_id == tenant_id, RiskAcceptance.risk_id == risk_id)
                .order_by(RiskAcceptance.created_at.desc())
            )
        ).scalars()

        def person(mid: uuid.UUID | None) -> Person | None:
            return Person(mid, names.get(mid, "Former member")) if mid else None

        return [
            AcceptanceView(
                id=a.id,
                status=a.status,
                rationale=a.rationale,
                expires_on=a.expires_on,
                requested_by=person(a.requested_by_membership_id),
                approver=person(a.approver_membership_id),
                residual_score_at_request=a.residual_score_at_request,
                decided_at=a.decided_at,
                decision_note=a.decision_note,
                revoked_at=a.revoked_at,
                revoke_reason=a.revoke_reason,
                created_at=a.created_at,
            )
            for a in rows
        ]

    async def approvers(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, me: uuid.UUID | None
    ) -> list[ApproverView]:
        """Who could decide an acceptance, with the ineligible marked and reasoned."""
        from verity.core.deps import resolve_effective_permissions  # noqa: PLC0415
        from verity.modules.iam.service import iam_service  # noqa: PLC0415

        out: list[ApproverView] = []
        for member in await iam_service.list_members(session, tenant_id=tenant_id):
            if member.status != "active":
                continue
            reason = None
            if member.membership_id == me:
                reason = "You are requesting it"
            else:
                keys = await resolve_effective_permissions(
                    session, tenant_id=tenant_id, membership_id=member.membership_id
                )
                if "risks:approve" not in keys:
                    reason = "Cannot approve risks"
            out.append(ApproverView(member.membership_id, member.full_name, reason is None, reason))
        out.sort(key=lambda a: (not a.eligible, a.name.lower()))
        return out

    async def _load_acceptance(
        self, session: AsyncSession, risk: Risk, acceptance_id: uuid.UUID
    ) -> RiskAcceptance:
        row = await session.get(RiskAcceptance, acceptance_id, populate_existing=True)
        if row is None or row.tenant_id != risk.tenant_id or row.risk_id != risk.id:
            raise NotFound(_ACCEPTANCE_GONE, detail=f"acceptance {acceptance_id}")
        return row

    async def request_acceptance(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        approver_membership_id: uuid.UUID,
        rationale: str,
        expires_on: date,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        requester = _actor_id(actor)
        if risk.status == "closed":
            raise Conflict("A closed risk cannot be accepted.", detail="accept closed risk")
        if not _clean(rationale):
            raise InvalidInput(
                "Explain why the remaining risk is acceptable. The approver signs against it.",
                detail="acceptance without rationale",
            )
        if expires_on <= datetime.now(UTC).date():
            raise InvalidInput("Set an expiry date in the future.", detail=f"expiry {expires_on}")
        if approver_membership_id == requester:
            raise InvalidInput(
                "Choose someone else to approve. You cannot approve your own request.",
                detail="self approval",
            )
        eligible = {
            a.membership_id
            for a in await self.approvers(session, tenant_id=tenant_id, me=requester)
            if a.eligible
        }
        if approver_membership_id not in eligible:
            raise InvalidInput(
                "Choose an approver who can approve risk acceptances.",
                detail=f"approver {approver_membership_id} not eligible",
            )
        open_one = (
            await session.execute(
                select(RiskAcceptance.id).where(
                    RiskAcceptance.tenant_id == tenant_id,
                    RiskAcceptance.risk_id == risk.id,
                    RiskAcceptance.status.in_(("pending", "active")),
                )
            )
        ).first()
        if open_one is not None:
            raise Conflict(
                "This risk already has an acceptance pending or in force.",
                detail="acceptance already open",
            )
        await session.refresh(risk, ["inherent_score", "residual_score"])
        acceptance = RiskAcceptance(
            id=uuid7(),
            tenant_id=tenant_id,
            risk_id=risk.id,
            status="pending",
            rationale=(_clean(rationale) or "")[:4000],
            expires_on=expires_on,
            requested_by_membership_id=requester,
            approver_membership_id=approver_membership_id,
            residual_score_at_request=risk.residual_score or risk.inherent_score,
        )
        session.add(acceptance)
        await session.flush([acceptance])
        await self._event(
            session,
            risk,
            actor,
            "acceptance_requested",
            None,
            expires_on.isoformat(),
            acceptance.rationale,
        )
        await self._record(
            session,
            risk,
            actor,
            "create",
            None,
            {"acceptance": str(acceptance.id), "expires_on": expires_on.isoformat()},
        )
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        await notification_service.notify(
            session,
            tenant_id=tenant_id,
            recipient_membership_id=approver_membership_id,
            kind="risk_acceptance_requested",
            title=f"Approve acceptance of {risk.code}",
            body=risk.title,
            object_type="risk",
            object_id=risk.id,
            email=True,
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def decide_acceptance(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        acceptance_id: uuid.UUID,
        approve: bool,
        note: str | None,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        acceptance = await self._load_acceptance(session, risk, acceptance_id)
        if acceptance.status != "pending":
            raise Conflict(
                "This request has already been decided.", detail=f"status {acceptance.status}"
            )
        decider = _actor_id(actor)
        if decider is None or decider != acceptance.approver_membership_id:
            raise PermissionDenied(
                "Only the named approver can decide this request.",
                detail="decision by someone other than the approver",
            )
        if not approve and not _clean(note):
            raise InvalidInput("Say why the request is rejected.", detail="reject without note")
        acceptance.status = "active" if approve else "rejected"
        acceptance.decided_at = datetime.now(UTC)
        acceptance.decision_note = _clean(note)
        await session.flush([acceptance])
        if approve:
            if acceptance.expires_on <= datetime.now(UTC).date():
                raise Conflict(
                    "This request has expired. Ask for a new one.", detail="approve expired request"
                )
            await self._event(
                session,
                risk,
                actor,
                "acceptance_approved",
                risk.status,
                "accepted",
                acceptance.decision_note,
            )
            risk.status = "accepted"
            risk.treatment = "accept"
        else:
            await self._event(
                session, risk, actor, "acceptance_rejected", None, None, acceptance.decision_note
            )
        await session.flush([risk])
        await self._audit.record(
            session,
            action="approve",
            object_type="risk",
            object_id=risk.id,
            actor=actor,
            tenant_id=tenant_id,
            before={"acceptance": "pending"},
            after={"acceptance": acceptance.status, "note": acceptance.decision_note},
        )
        if acceptance.requested_by_membership_id:
            from verity.modules.notifications.service import notification_service  # noqa: PLC0415

            await notification_service.notify(
                session,
                tenant_id=tenant_id,
                recipient_membership_id=acceptance.requested_by_membership_id,
                kind="risk_acceptance_decided",
                title=f"Acceptance of {risk.code} {'approved' if approve else 'rejected'}",
                body=acceptance.decision_note or risk.title,
                object_type="risk",
                object_id=risk.id,
            )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def withdraw_acceptance(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        acceptance_id: uuid.UUID,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        acceptance = await self._load_acceptance(session, risk, acceptance_id)
        if acceptance.status != "pending":
            raise Conflict(
                "Only a pending request can be withdrawn.", detail=f"status {acceptance.status}"
            )
        if _actor_id(actor) != acceptance.requested_by_membership_id:
            raise PermissionDenied(
                "Only the person who asked can withdraw the request.", detail="withdraw by other"
            )
        acceptance.status = "withdrawn"
        await session.flush([acceptance])
        await self._event(session, risk, actor, "acceptance_withdrawn")
        await self._record(
            session, risk, actor, "update", {"acceptance": "pending"}, {"acceptance": "withdrawn"}
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def revoke_acceptance(  # noqa: PLR0913
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        risk_id: uuid.UUID,
        acceptance_id: uuid.UUID,
        reason: str,
    ) -> RiskDetailView:
        risk = await self._load(session, tenant_id, risk_id)
        acceptance = await self._load_acceptance(session, risk, acceptance_id)
        if acceptance.status != "active":
            raise Conflict(
                "Only an acceptance in force can be revoked.", detail=f"status {acceptance.status}"
            )
        if not _clean(reason):
            raise InvalidInput("Say why the acceptance is revoked.", detail="revoke without reason")
        acceptance.status = "revoked"
        acceptance.revoked_at = datetime.now(UTC)
        acceptance.revoked_by_membership_id = _actor_id(actor)
        acceptance.revoke_reason = _clean(reason)
        await session.flush([acceptance])
        await self._event(
            session, risk, actor, "acceptance_revoked", "accepted", "open", acceptance.revoke_reason
        )
        if risk.status == "accepted":
            risk.status = "open"
        await session.flush([risk])
        await self._record(
            session, risk, actor, "transition", {"status": "accepted"}, {"status": risk.status}
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)

    async def _settle_acceptances(
        self, session: AsyncSession, risk: Risk, actor: Actor, status: str, reason: str
    ) -> None:
        """Close any acceptance still pending or in force when the risk itself closes."""
        rows = (
            await session.execute(
                select(RiskAcceptance).where(
                    RiskAcceptance.tenant_id == risk.tenant_id,
                    RiskAcceptance.risk_id == risk.id,
                    RiskAcceptance.status.in_(("pending", "active")),
                )
            )
        ).scalars()
        now = datetime.now(UTC)
        for row in rows:
            row.status = "withdrawn" if row.status == "pending" else status
            if row.status == "revoked":
                row.revoked_at = now
                row.revoked_by_membership_id = _actor_id(actor)
                row.revoke_reason = reason
        await session.flush()

    async def expire_acceptances(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
        """Expire lapsed acceptances and reopen their risks (R7). Idempotent."""
        today = datetime.now(UTC).date()
        rows = list(
            (
                await session.execute(
                    select(RiskAcceptance).where(
                        RiskAcceptance.tenant_id == tenant_id,
                        RiskAcceptance.status.in_(("active", "pending")),
                        RiskAcceptance.expires_on < today,
                    )
                )
            ).scalars()
        )
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        system = System()
        for acceptance in rows:
            was_active = acceptance.status == "active"
            acceptance.status = "expired"
            await session.flush([acceptance])
            risk = await self._load(session, tenant_id, acceptance.risk_id)
            if not was_active:
                continue
            await self._event(
                session,
                risk,
                system,
                "acceptance_expired",
                "accepted",
                "open",
                acceptance.expires_on.isoformat(),
            )
            if risk.status == "accepted":
                risk.status = "open"
            await session.flush([risk])
            await self._record(
                session, risk, system, "transition", {"status": "accepted"}, {"status": risk.status}
            )
            if risk.owner_membership_id:
                await notification_service.notify_once(
                    session,
                    tenant_id=tenant_id,
                    recipient_membership_id=risk.owner_membership_id,
                    kind="risk_acceptance_expired",
                    title=f"Acceptance of {risk.code} expired",
                    body=f"{risk.title} is open again and needs a treatment decision.",
                    object_type="risk",
                    object_id=risk.id,
                    email=True,
                )
        return len(rows)

    async def notify_reviews_due(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> int:
        """One notice per overdue review per owner. Idempotent through notify_once."""
        from verity.modules.notifications.service import notification_service  # noqa: PLC0415

        today = datetime.now(UTC).date()
        rows = (
            await session.execute(
                select(Risk).where(
                    Risk.tenant_id == tenant_id,
                    Risk.status != "closed",
                    Risk.next_review_on < today,
                    Risk.owner_membership_id.is_not(None),
                )
            )
        ).scalars()
        written = 0
        for risk in rows:
            assert risk.owner_membership_id is not None  # noqa: S101 — filtered above
            written += int(
                await notification_service.notify_once(
                    session,
                    tenant_id=tenant_id,
                    recipient_membership_id=risk.owner_membership_id,
                    kind="risk_review_due",
                    title=f"{risk.code} is due for review",
                    body=risk.title,
                    object_type="risk",
                    object_id=risk.id,
                )
            )
        return written

    # =========================================================================
    # Overview
    # =========================================================================

    async def summary(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> dict[str, Any]:
        register = await self._load_register(session, tenant_id, register_id)
        risks = list(
            (
                await session.execute(
                    select(Risk).where(Risk.tenant_id == tenant_id, Risk.register_id == register.id)
                )
            ).scalars()
        )
        views = await self._views(session, tenant_id, register, risks)
        live = [v for v in views if v.status != "closed"]
        rows, cols = register.likelihood_levels, register.impact_levels
        inherent = [[0] * cols for _ in range(rows)]
        residual = [[0] * cols for _ in range(rows)]
        by_band: Counter[str] = Counter()
        by_appetite: Counter[str] = Counter()
        attention: Counter[str] = Counter()
        by_treatment: Counter[str] = Counter()
        by_category: Counter[str] = Counter()
        for v in live:
            if v.inherent_likelihood and v.inherent_impact:
                inherent[v.inherent_likelihood - 1][v.inherent_impact - 1] += 1
            if v.residual_likelihood and v.residual_impact:
                residual[v.residual_likelihood - 1][v.residual_impact - 1] += 1
            by_band[v.residual_band or v.inherent_band or "unscored"] += 1
            if v.appetite_status:
                by_appetite[v.appetite_status] += 1
            by_treatment[v.treatment or "undecided"] += 1
            by_category[v.category_name] += 1
            attention.update(v.attention)
        by_status = Counter(v.status for v in views)
        ranked = sorted(
            (v for v in live if (v.residual_score or v.inherent_score)),
            key=lambda v: (-(v.residual_score or v.inherent_score or 0), v.code),
        )
        return {
            "register_id": register.id,
            "total": len(live),
            "closed": by_status.get("closed", 0),
            "likelihood_levels": rows,
            "impact_levels": cols,
            "heatmap_inherent": inherent,
            "heatmap_residual": residual,
            "by_band": dict(by_band),
            "by_appetite": dict(by_appetite),
            "by_status": {s: by_status.get(s, 0) for s in RISK_STATUSES},
            "by_treatment": dict(by_treatment),
            "by_category": [
                {"name": name, "count": count} for name, count in by_category.most_common()
            ],
            "attention": dict(attention),
            "top_risks": ranked[:_TOP_RISKS],
        }

    async def facets(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> dict[str, Any]:
        summary = await self.summary(session, tenant_id=tenant_id, register_id=register_id)
        return {
            "statuses": summary["by_status"],
            "bands": summary["by_band"],
            "treatments": summary["by_treatment"],
            "attention": summary["attention"],
        }

    # =========================================================================
    # Starter library
    # =========================================================================

    async def list_library(
        self, session: AsyncSession, *, tenant_id: uuid.UUID, register_id: uuid.UUID
    ) -> list[TemplateView]:
        register = await self._load_register(session, tenant_id, register_id)
        adopted = set(
            (
                await session.execute(
                    select(Risk.template_id).where(
                        Risk.tenant_id == tenant_id,
                        Risk.register_id == register.id,
                        Risk.template_id.is_not(None),
                    )
                )
            ).scalars()
        )
        templates = (
            await session.execute(
                select(RiskTemplate).order_by(RiskTemplate.category, RiskTemplate.code)
            )
        ).scalars()
        return [
            TemplateView(
                id=t.id,
                code=t.code,
                title=t.title,
                description=t.description,
                category=t.category,
                sub_category=t.sub_category,
                default_likelihood=t.default_likelihood,
                default_impact=t.default_impact,
                root_cause=t.root_cause,
                consequences=t.consequences,
                recommendations=t.recommendations,
                treatment=t.treatment,
                control_keys=list(t.control_keys or []),
                frameworks=list(t.frameworks or []),
                adopted=t.id in adopted,
            )
            for t in templates
        ]

    async def library_templates(self, session: AsyncSession) -> list[RiskTemplate]:
        return list((await session.execute(select(RiskTemplate))).scalars())

    def match_category(
        self, categories: Sequence[RiskCategory], category: str | None, sub_category: str | None
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        """Map category names onto a register's taxonomy, by case-insensitive name."""
        live = [c for c in categories if c.archived_at is None]
        parents = {c.name.lower(): c for c in live if c.parent_id is None}
        parent = parents.get((category or "").lower()) or parents.get(_DEFAULT_CATEGORY.lower())
        if parent is None and parents:
            parent = next(iter(parents.values()))
        if parent is None:
            return None, None
        child = None
        if sub_category:
            child = next(
                (
                    c
                    for c in live
                    if c.parent_id == parent.id and c.name.lower() == sub_category.lower()
                ),
                None,
            )
        return parent.id, child.id if child else None

    async def adopt_templates(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        register_id: uuid.UUID,
        codes: Sequence[str],
    ) -> dict[str, int]:
        """Copy library risks into a register and link their suggested controls (R11)."""
        register = await self._load_register(session, tenant_id, register_id)
        wanted = list(dict.fromkeys(codes))
        if not wanted:
            raise InvalidInput("Choose at least one library risk.", detail="adopt nothing")
        templates = {
            t.code: t
            for t in (
                await session.execute(select(RiskTemplate).where(RiskTemplate.code.in_(wanted)))
            ).scalars()
        }
        adopted_already = set(
            (
                await session.execute(
                    select(Risk.template_id).where(
                        Risk.tenant_id == tenant_id,
                        Risk.register_id == register.id,
                        Risk.template_id.is_not(None),
                    )
                )
            ).scalars()
        )
        categories = await self._categories(session, tenant_id, register.id)
        from verity.modules.compliance.control_service import control_service  # noqa: PLC0415

        all_keys = sorted({k for t in templates.values() for k in (t.control_keys or [])})
        control_ids = await control_service.control_ids_for_keys(
            session, tenant_id=tenant_id, keys=all_keys
        )
        codes_by_id = {
            c.id: c.code
            for c in await control_service.list_controls(session, tenant_id=tenant_id)
            if c.id in set(control_ids.values())
        }
        number = await self._next_code(session, tenant_id)
        created = skipped = linked = 0
        for code in wanted:
            template = templates.get(code)
            if template is None or template.id in adopted_already:
                skipped += 1
                continue
            category_id, sub_category_id = self.match_category(
                categories, template.category, template.sub_category
            )
            if category_id is None:
                raise Conflict(
                    "This register has no categories. Add one in settings first.",
                    detail="adopt into empty taxonomy",
                )
            likelihood = scoring.rescale(template.default_likelihood, register.likelihood_levels)
            impact = scoring.rescale(template.default_impact, register.impact_levels)
            risk = await self.create_risk(
                session,
                tenant_id=tenant_id,
                actor=actor,
                data=RiskInput(
                    register_id=register.id,
                    title=template.title,
                    description=template.description,
                    category_id=category_id,
                    sub_category_id=sub_category_id,
                    inherent_likelihood=likelihood,
                    inherent_impact=impact,
                    root_cause=template.root_cause,
                    consequences=template.consequences,
                    recommendations=template.recommendations,
                    treatment=template.treatment if template.treatment in TREATMENTS else None,
                ),
                origin="library",
                template_id=template.id,
                code_number=number,
            )
            number += 1
            created += 1
            mapped = [control_ids[k] for k in (template.control_keys or []) if k in control_ids]
            linked += await self._add_controls(
                session, risk, actor, mapped, known_codes=codes_by_id
            )
        await session.flush()
        return {"created": created, "skipped": skipped, "controls_linked": linked}

    # =========================================================================
    # Vendor finding promotion (spec ¶85)
    # =========================================================================

    async def promote_vendor_finding(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor: Actor,
        finding_id: uuid.UUID,
        register_id: uuid.UUID,
    ) -> RiskDetailView:
        from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

        finding = await vendor_service.get_finding(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        if finding.promoted_risk_id is not None:
            raise Conflict(
                "This finding is already in the risk register.",
                detail=f"finding promoted to {finding.promoted_risk_id}",
            )
        register = await self._load_register(session, tenant_id, register_id)
        categories = await self._categories(session, tenant_id, register.id)
        category_id, sub_category_id = self.match_category(categories, "Third party", "Vendor")
        if category_id is None:
            raise Conflict(
                "This register has no categories. Add one in settings first.",
                detail="promote into empty taxonomy",
            )
        severity_level = {"critical": 5, "high": 4, "medium": 3, "low": 2}.get(finding.severity, 3)
        risk = await self.create_risk(
            session,
            tenant_id=tenant_id,
            actor=actor,
            data=RiskInput(
                register_id=register.id,
                title=f"{finding.vendor_name}: {finding.title}"
                if finding.vendor_name
                else finding.title,
                description=finding.detail,
                category_id=category_id,
                sub_category_id=sub_category_id,
                inherent_likelihood=scoring.rescale(3, register.likelihood_levels),
                inherent_impact=scoring.rescale(severity_level, register.impact_levels),
                owner_membership_id=finding.owner_membership_id,
            ),
            origin="vendor_finding",
            origin_ref=finding.id,
        )
        await self._link(session, risk, actor, "vendor", finding.vendor_id)
        await vendor_service.mark_finding_promoted(
            session, tenant_id=tenant_id, actor=actor, finding_id=finding.id, risk_id=risk.id
        )
        return await self.get_risk(session, tenant_id=tenant_id, risk_id=risk.id)


risk_service = RiskService()
"""Module-level singleton, imported by the router, the jobs and sibling services."""

__all__ = [
    "ACCEPTANCE_STATUSES",
    "LINKABLE_TYPES",
    "CategoryNode",
    "RegisterInput",
    "RiskFilters",
    "RiskInput",
    "RiskService",
    "risk_service",
]
