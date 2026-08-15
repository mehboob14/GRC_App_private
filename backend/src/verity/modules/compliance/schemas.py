"""Response models for the compliance module.

Read-only in Week 2 Stage 2: this module serves shipped global content
(frameworks, their requirements, and the control template library) and writes
nothing, so there are no request models and no audit rows yet.

Every field here is content the platform ships. Nothing on these responses is
derived from a tenant's own data — readiness, coverage and control counts per
tenant arrive with the tenant control library, and are deliberately absent
rather than stubbed with a zero that would read as a real measurement.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from verity.modules.tenancy.schemas import UtcDateTime


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FrameworkVersionOut(_Response):
    id: uuid.UUID
    version: str
    published_at: UtcDateTime
    is_current: bool
    requirement_count: int


class FrameworkOut(_Response):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    built_in: bool
    versions: list[FrameworkVersionOut]


class RequirementOut(_Response):
    id: uuid.UUID
    requirement_key: str
    code: str
    name: str
    description: str | None
    category: str
    trust_services_category: str
    is_always_in_scope: bool
    # How many shipped control templates claim to satisfy this criterion. A
    # criterion with zero is a genuine gap in the library, so the number is
    # counted, never defaulted.
    template_count: int


class ControlTemplateOut(_Response):
    id: uuid.UUID
    code: str
    canonical_key: str
    name: str
    description: str
    implementation_guidance: str | None
    category: str
    control_type: str
    control_sub_type: str | None
    importance: str
    built_in: bool


class ControlTemplateDetailOut(ControlTemplateOut):
    """One template plus the criteria it satisfies — the 'collect once, satisfy
    many' relationship made visible."""

    requirements: list[RequirementOut]


class ControlTemplatePage(_Response):
    items: list[ControlTemplateOut]
    total: int
