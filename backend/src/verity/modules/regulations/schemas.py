"""Wire shapes for the country reference panel."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from verity.modules.tenancy.schemas import UtcDateTime


class RegulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    jurisdiction: str
    zone: str | None
    short_name: str
    official_name: str
    regulator: str | None
    kinds: list[str]
    topic_column: str
    force: str
    state: str
    state_note: str | None
    tier: str
    applies_to: str
    duties: list[dict[str, Any]]
    assurance: dict[str, Any]
    iso27001: dict[str, Any]
    soc2: dict[str, Any]
    helps: list[str]
    not_covered: list[str]
    milestones: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    review_status: str
    review_overdue: bool
    confidence: str
    because: list[str]
    relevance: str | None
    note: str | None
    decided_by_name: str | None
    decided_at: UtcDateTime | None
    in_register_since: UtcDateTime | None = None


class PanelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    regulations: list[RegulationOut]
    hidden_drafts: int
    uncovered: list[str]
    disclaimer: str


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevance: str = Field(pattern="^(relevant|not_relevant)$")
    note: str | None = Field(default=None, max_length=1000)
