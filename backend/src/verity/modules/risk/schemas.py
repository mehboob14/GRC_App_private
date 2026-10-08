"""Request and response contracts for the risk register.

Responses build from the service's view dataclasses through ``from_attributes``;
the frontend's ``features/risk/types.ts`` mirrors these shapes.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- registers ---------------------------------------------------------------


class CategoryOut(_Response):
    id: uuid.UUID
    name: str
    position: int
    archived: bool
    risk_count: int
    children: list[CategoryOut] = []


class RegisterOut(_Response):
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
    categories: list[CategoryOut]
    created_at: UtcDateTime
    scoring_formula: dict[str, Any]
    appetite: dict[str, Any]
    max_score: int


class ScaleLevelIn(_Request):
    label: str = Field(max_length=40)
    description: str = Field(default="", max_length=200)


class BandIn(_Request):
    key: str
    label: str = Field(max_length=24)
    min_score: int


class RegisterWrite(_Request):
    name: str = Field(min_length=1, max_length=120)
    register_type: str = "enterprise"
    description: str | None = Field(default=None, max_length=2000)
    owner_membership_id: uuid.UUID | None = None
    likelihood_levels: int | None = None
    impact_levels: int | None = None
    likelihood_scale: list[ScaleLevelIn] | None = None
    impact_scale: list[ScaleLevelIn] | None = None
    severity_bands: list[BandIn] | None = None
    review_cadence_days: int | None = None
    is_default: bool | None = None
    status: str | None = None
    scoring_formula: dict[str, Any] | None = None
    appetite: dict[str, Any] | None = None


class CategoryNodeIn(_Request):
    id: uuid.UUID | None = None
    name: str = Field(max_length=80)
    children: list[CategoryNodeIn] = []


class CategoriesWrite(_Request):
    categories: list[CategoryNodeIn] = Field(max_length=60)


class CustomFieldOut(_Response):
    """One tenant-defined field, as the settings screen and the form read it."""

    id: uuid.UUID
    key: str
    label: str
    field_type: str
    options: list[str]
    help_text: str | None
    required: bool
    position: int
    archived: bool


class CustomFieldPageOut(_Response):
    items: list[CustomFieldOut]


class CustomFieldWrite(_Request):
    label: str = Field(min_length=1, max_length=80)
    field_type: str = Field(default="text", pattern="^(text|textarea|number|date|select|checkbox)$")
    options: list[str] = Field(default_factory=list, max_length=50)
    help_text: str | None = Field(default=None, max_length=300)
    required: bool = False
    position: int = Field(default=0, ge=0, le=999)


class CustomFieldArchiveWrite(_Request):
    archived: bool = True


# -- risks ---------------------------------------------------------------------


class PersonOut(_Response):
    membership_id: uuid.UUID
    name: str


class RiskOut(_Response):
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
    owner: PersonOut | None
    department_group_id: uuid.UUID | None
    department_name: str | None
    treatment_due_on: date | None
    next_review_on: date | None
    last_reviewed_at: UtcDateTime | None
    origin: str
    control_count: int
    attention: list[str]
    created_at: UtcDateTime
    updated_at: UtcDateTime
    appetite_status: str | None = None
    custom_fields: dict[str, Any] = {}


class RiskPageOut(_Response):
    items: list[RiskOut]
    total: int


class ControlRefOut(_Response):
    id: uuid.UUID
    code: str
    name: str
    status: str
    category: str
    disabled: bool


class LinkedRecordOut(_Response):
    link_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relation: str
    code: str
    title: str
    status: str
    detail: str | None


class ActionOut(_Response):
    link_id: uuid.UUID
    task_id: uuid.UUID
    code: str
    title: str
    status: str
    priority: str
    owner_name: str | None
    due_at: UtcDateTime | None


class AcceptanceOut(_Response):
    id: uuid.UUID
    status: str
    rationale: str
    expires_on: date
    requested_by: PersonOut | None
    approver: PersonOut | None
    residual_score_at_request: int | None
    decided_at: UtcDateTime | None
    decision_note: str | None
    revoked_at: UtcDateTime | None
    revoke_reason: str | None
    created_at: UtcDateTime


class EventOut(_Response):
    id: uuid.UUID
    kind: str
    from_value: str | None
    to_value: str | None
    note: str | None
    inherent_score: int | None
    residual_score: int | None
    actor_name: str | None
    created_at: UtcDateTime


class RiskDetailOut(RiskOut):
    root_cause: str | None
    consequences: str | None
    recommendations: str | None
    treatment_plan: str | None
    closure_justification: str | None
    closed_at: UtcDateTime | None
    template_code: str | None
    origin_ref: uuid.UUID | None
    created_by_name: str | None
    allowed_statuses: list[str]
    controls: list[ControlRefOut]
    links: list[LinkedRecordOut]
    actions: list[ActionOut]
    acceptances: list[AcceptanceOut]
    history: list[EventOut]


class RiskWrite(_Request):
    register_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=10000)
    category_id: uuid.UUID
    sub_category_id: uuid.UUID | None = None
    status: str = "open"
    treatment: str | None = None
    inherent_likelihood: int | None = None
    inherent_impact: int | None = None
    residual_likelihood: int | None = None
    residual_impact: int | None = None
    root_cause: str | None = Field(default=None, max_length=10000)
    consequences: str | None = Field(default=None, max_length=10000)
    recommendations: str | None = Field(default=None, max_length=10000)
    treatment_plan: str | None = Field(default=None, max_length=10000)
    owner_membership_id: uuid.UUID | None = None
    department_group_id: uuid.UUID | None = None
    treatment_due_on: date | None = None
    next_review_on: date | None = None
    asset_ids: list[uuid.UUID] | None = Field(default=None, max_length=200)
    custom_fields: dict[str, Any] | None = None


class StatusWrite(_Request):
    status: str
    note: str | None = Field(default=None, max_length=4000)


class ReviewWrite(_Request):
    note: str | None = Field(default=None, max_length=4000)
    next_review_on: date | None = None


class ControlsWrite(_Request):
    control_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class LinkWrite(_Request):
    target_type: str
    target_id: uuid.UUID


class ActionWrite(_Request):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: str = "medium"
    owner_membership_id: uuid.UUID | None = None
    due_on: date | None = None


class AcceptanceWrite(_Request):
    approver_membership_id: uuid.UUID
    rationale: str = Field(min_length=1, max_length=4000)
    expires_on: date


class DecisionWrite(_Request):
    approve: bool
    note: str | None = Field(default=None, max_length=4000)


class RevokeWrite(_Request):
    reason: str = Field(min_length=1, max_length=4000)


class MemberOptionOut(_Response):
    membership_id: uuid.UUID
    name: str
    email: str


class UnitOptionOut(_Response):
    id: uuid.UUID
    name: str


class OptionsOut(_Response):
    members: list[MemberOptionOut]
    business_units: list[UnitOptionOut]


class ApproverOut(_Response):
    membership_id: uuid.UUID
    name: str
    eligible: bool
    reason: str | None


class RiskRefOut(_Response):
    id: uuid.UUID
    code: str
    title: str
    status: str
    band: str | None
    register_name: str


# -- overview ------------------------------------------------------------------


class CategoryCountOut(_Response):
    name: str
    count: int


class SummaryOut(_Response):
    register_id: uuid.UUID
    total: int
    closed: int
    likelihood_levels: int
    impact_levels: int
    heatmap_inherent: list[list[int]]
    heatmap_residual: list[list[int]]
    by_band: dict[str, int]
    by_appetite: dict[str, int] = {}
    by_status: dict[str, int]
    by_treatment: dict[str, int]
    by_category: list[CategoryCountOut]
    attention: dict[str, int]
    top_risks: list[RiskOut]


class FacetsOut(_Response):
    statuses: dict[str, int]
    bands: dict[str, int]
    treatments: dict[str, int]
    attention: dict[str, int]


# -- library, import, assist, promotion -------------------------------------------


class TemplateOut(_Response):
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


class AdoptWrite(_Request):
    register_id: uuid.UUID
    codes: list[str] = Field(min_length=1, max_length=300)


class AdoptOut(_Response):
    created: int
    skipped: int
    controls_linked: int


class ImportRowOut(_Response):
    row_number: int
    title: str
    description: str
    category_id: uuid.UUID | None
    category_name: str | None
    sub_category_id: uuid.UUID | None
    sub_category_name: str | None
    status: str
    owner_membership_id: uuid.UUID | None
    owner_name: str | None
    department_group_id: uuid.UUID | None
    department_name: str | None
    inherent_likelihood: int | None
    inherent_impact: int | None
    residual_likelihood: int | None
    residual_impact: int | None
    root_cause: str | None
    consequences: str | None
    recommendations: str | None
    treatment: str | None
    treatment_plan: str | None
    treatment_due_on: date | None
    next_review_on: date | None
    custom_fields: dict[str, Any] = {}
    errors: list[str]
    warnings: list[str]


class ImportPreviewOut(_Response):
    rows: list[ImportRowOut]
    valid: int
    invalid: int


class ImportRowIn(_Request):
    row_number: int
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    category_id: uuid.UUID | None
    sub_category_id: uuid.UUID | None = None
    status: str = "open"
    owner_membership_id: uuid.UUID | None = None
    department_group_id: uuid.UUID | None = None
    inherent_likelihood: int | None = None
    inherent_impact: int | None = None
    residual_likelihood: int | None = None
    residual_impact: int | None = None
    root_cause: str | None = None
    consequences: str | None = None
    recommendations: str | None = None
    treatment: str | None = None
    treatment_plan: str | None = None
    treatment_due_on: date | None = None
    next_review_on: date | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class ImportWrite(_Request):
    register_id: uuid.UUID
    rows: list[ImportRowIn] = Field(min_length=1, max_length=2000)


class ImportFailureOut(_Response):
    row_number: int
    error: str


class ImportResultOut(_Response):
    created: int
    failed: list[ImportFailureOut]


class AssistWrite(_Request):
    register_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)


class SimilarOut(_Response):
    code: str
    title: str


class AssistOut(_Response):
    source: str
    description: str | None
    root_cause: str | None
    consequences: str | None
    recommendations: str | None
    treatment_plan: str | None
    treatment: str | None
    category_id: uuid.UUID | None
    sub_category_id: uuid.UUID | None
    inherent_likelihood: int | None
    inherent_impact: int | None
    residual_likelihood: int | None
    residual_impact: int | None
    similar: list[SimilarOut]


class PromoteWrite(_Request):
    finding_id: uuid.UUID
    register_id: uuid.UUID
