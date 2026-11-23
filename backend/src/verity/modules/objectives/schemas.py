"""Wire shapes for assessment objectives."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NextStepOut(_Out):
    action: str
    label: str
    link: str
    artifact_key: str | None


class ArtifactOut(_Out):
    key: str
    code: str
    name: str
    category: str
    state: str
    reason: str | None
    sources: list[str]


class ObjectiveOut(_Out):
    code: str
    key: str
    statement: str
    assurance: str
    methods: list[str]
    interview_with: list[str] = []
    outcome: str
    reason: str | None
    artifacts: list[ArtifactOut]
    next_step: NextStepOut | None
    not_applicable_reason: str | None


class ControlObjectivesOut(_Out):
    control_id: uuid.UUID
    code: str
    name: str
    frameworks: list[str]
    objectives: list[ObjectiveOut]
    design_ready: bool
    operating_ready: bool
    ready: bool
    ready_today: bool
    review_status: str


class FrameworkObjectivesOut(_Out):
    code: str
    name: str
    audit_type: str | None
    controls: int
    design_ready: int
    operating_ready: int
    objectives_total: int
    objectives_satisfied: int
    first_audit_ready: int
    first_audit_label: str
    first_audit_notes: list[str]


class NextItemOut(_Out):
    control_id: uuid.UUID
    control_code: str
    control_name: str
    objective: ObjectiveOut


class OverviewOut(_Out):
    frameworks: list[FrameworkObjectivesOut]
    controls_with_objectives: int
    controls_total: int
    next: list[NextItemOut]
    review_status: str


class ComparisonRowOut(_Out):
    control_id: uuid.UUID
    code: str
    name: str
    ready_today: bool
    ready_rule_a: bool
    ready_rule_b: bool
    blocking: list[str]


class ComparisonOut(_Out):
    rows: list[ComparisonRowOut]
    compared: int
    differ_rule_a: int
    differ_rule_b: int


class NotApplicableIn(_In):
    reason: str = Field(min_length=1, max_length=1000)


class TagIn(_In):
    evidence_id: uuid.UUID
    on: bool = True
