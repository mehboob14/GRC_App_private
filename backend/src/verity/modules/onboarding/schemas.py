"""Wire shapes for Get Started."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.onboarding.service import REASON_MAX
from verity.modules.tenancy.schemas import UtcDateTime


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FrameworkFiguresOut(_Response):
    """One framework's separate figures. There is deliberately no blended score."""

    code: str
    name: str
    scope_model: str
    scope_set: bool
    audit_type: str | None
    window_start: date | None
    window_end: date | None
    audit_on: date | None
    certification_body: str | None
    as_of_date: date | None
    target_date: date | None
    live_date: date | None
    assessor: str
    requirements_total: int
    requirements_supported: int
    requirements_met: int
    controls_total: int
    controls_owned: int
    controls_evidenced: int
    checks_passing: int
    checks_failing: int
    decisions_total: int
    decisions_reviewed: int


class SkipOut(_Response):
    by_membership_id: uuid.UUID | None
    by_name: str | None
    at: UtcDateTime
    reason: str


class StepOut(_Response):
    key: str
    step: str
    phase: str
    title: str
    framework_code: str | None
    frameworks: list[str]
    state: str
    done_count: int | None
    total_count: int | None
    detail: str | None
    link: str
    can_act: bool
    skip: SkipOut | None


class MilestoneOut(_Response):
    kind: str
    label: str
    planned_on: date | None
    actual_on: date | None
    from_engagement: bool


class StatusOut(_Response):
    frameworks: list[FrameworkFiguresOut] | None
    steps: list[StepOut]
    next_key: str | None
    phases: list[str]
    milestones: dict[str, list[MilestoneOut]]


class SkipIn(_Request):
    reason: str = Field(min_length=1, max_length=REASON_MAX)


class OwnerFunctionOut(_Response):
    key: str
    label: str
    membership_id: uuid.UUID | None
    member_name: str | None
    controls: int


class OwnershipOut(_Response):
    functions: list[OwnerFunctionOut]
    controls_total: int
    controls_unowned: int
    would_change: int
    warnings: list[str]
    reassign: list[str] = []


class OwnerFunctionIn(_Request):
    membership_id: uuid.UUID | None


class ApplyOwnersIn(_Request):
    keep_existing: bool = True


class AppliedOut(_Response):
    changed: int


class RequiredRowOut(_Response):
    number: int
    title: str
    kind: str
    template: str | None
    template_available: bool
    product: str | None
    frameworks: list[str]
    controls: list[str]
    acknowledge: bool
    state: str
    document_id: uuid.UUID | None
    owner_membership_id: uuid.UUID | None


class HiddenRowOut(_Response):
    number: int
    title: str
    because: str


class RequiredOut(_Response):
    rows: list[RequiredRowOut]
    hidden: list[HiddenRowOut]
    counted: int
    approved: int
    in_review: int


class ProposalOut(_Response):
    key: str
    rule_key: str
    kind: str
    subject: str
    subject_name: str
    change: str
    because: str
    reason: str
    bulk_ok: bool
    framework: str | None
    state: str
    decided_by_name: str | None
    decided_at: UtcDateTime | None


class ProposalsOut(_Response):
    proposals: list[ProposalOut]
    open: int
    review_needed: int


class DecideIn(_Request):
    keys: list[str] = Field(min_length=1, max_length=200)
    accept: bool
    reason: str | None = Field(default=None, max_length=2000)
    bulk: bool = False


class DecidedOut(_Response):
    decided: int


class BaselineControlOut(_Response):
    id: uuid.UUID
    code: str
    name: str
    answer: str | None
    note: str | None


class BaselineFamilyOut(_Response):
    family: str
    controls: list[BaselineControlOut]
    answered: int


class BaselineOut(_Response):
    id: uuid.UUID | None
    status: str
    families: list[BaselineFamilyOut]
    answered: int
    total: int
    counts: dict[str, int]
    completed_at: UtcDateTime | None


class BaselineAnswerIn(_Request):
    answer: str = Field(pattern="^(in_place|partly|not_in_place|not_sure)$")
    note: str | None = Field(default=None, max_length=1000)


class SnapshotOut(_Response):
    id: uuid.UUID
    label: str
    figures: dict[str, object]
    created_at: UtcDateTime


class PlanItemOut(_Response):
    key: str
    kind: str
    title: str
    control_code: str
    owner_membership_id: uuid.UUID | None
    due_on: date | None
    raised: bool


class PlanOut(_Response):
    items: list[PlanItemOut]
    raised: int
    due_on: date | None
    due_label: str | None


class RaisedOut(_Response):
    raised: int


class SetupOut(_Response):
    start_point: str | None
    setup_step: str | None
    completed_at: UtcDateTime | None
    steps: list[str]


class SetupIn(_Request):
    start_point: str | None = Field(default=None, pattern="^(fresh|existing)$")
    setup_step: str | None = Field(default=None, max_length=40)
    complete: bool = False


class ConnectionSuggestionOut(_Response):
    key: str
    name: str
    because: str
    status: str
    connected: bool


class AssistIn(_Request):
    kind: str = Field(
        pattern="^(scope_statement|description_section|control_explanation|proposal_reason|document_tailoring)$"
    )
    subject: str | None = Field(default=None, max_length=120)


class DraftOut(_Response):
    kind: str
    source: str
    text: str
    notice: str | None
    model: str | None
    prompt_version: str
    at: UtcDateTime


class MyItemOut(_Response):
    kind: str
    title: str
    link: str


class MyPartOut(_Response):
    items: list[MyItemOut]


class PrefillOut(_Response):
    key: str
    value: object
    source: str


class AssignSectionIn(_Request):
    membership_id: uuid.UUID
