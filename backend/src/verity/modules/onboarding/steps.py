"""The Get Started step catalogue.

One list, in the order a programme is built (part 3 of the guided onboarding plan). Each
step names the permission needed to see its figure, the permission needed to act on it,
and the page it opens. Its done rule lives in ``service.py`` under the same key.

A step appears only when the workspace has records that can answer "is this done?" today.
Steps whose records arrive in later phases of the plan (owner functions, required
documents, audit records) are added with them, never shown early as a permanent zero.

``each`` marks a step that repeats for every active framework of that scope model
(``categories`` is SOC 2, ``applicability`` is ISO 27001 and the frameworks built like it).
Its key then carries the framework code, so a skip on ISO 27001 never hides SOC 2's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

Phase = Literal["describe", "organise", "assess", "build", "operate", "check", "audit"]
PHASES: Final[tuple[Phase, ...]] = (
    "describe",
    "organise",
    "assess",
    "build",
    "operate",
    "check",
    "audit",
)


@dataclass(frozen=True, slots=True)
class StepDef:
    key: str
    phase: Phase
    title: str
    read: str
    """Permission needed to see the step's figure. Without it the step reads not permitted."""
    act: str
    """Permission needed to do the work the step links to."""
    link: str
    """Path the step opens. ``{framework}`` is replaced by the framework code."""
    each: Literal["categories", "applicability", "any"] | None = None
    """Repeat for every active framework of that scope model; ``any`` for every framework."""


STEPS: Final[tuple[StepDef, ...]] = (
    StepDef(
        "profile",
        "describe",
        "Complete your company profile",
        read="tenant:read",
        act="tenant:manage",
        link="/settings/organization/profile",
    ),
    StepDef(
        "report",
        "describe",
        "Choose your report type and categories",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/scope?framework={framework}",
        each="categories",
    ),
    StepDef(
        "auditor",
        "describe",
        "Name your auditor",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/scope?framework={framework}",
        each="any",
    ),
    StepDef(
        "scope_statement",
        "describe",
        "Write your scope statement",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/scope?framework={framework}",
        each="applicability",
    ),
    StepDef(
        "applicability",
        "describe",
        "Decide what applies",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/soa?framework={framework}",
        each="applicability",
    ),
    StepDef(
        "suggestions",
        "describe",
        "Review suggestions from your profile",
        read="frameworks:read",
        act="controls:manage",
        link="/quick-start/suggestions",
    ),
    StepDef(
        "own_mfa",
        "organise",
        "Turn on two factor sign in for your account",
        read="tenant:read",
        act="tenant:read",
        link="/settings/security/mfa",
    ),
    StepDef(
        "admin_mfa",
        "organise",
        "Require two factor sign in for admins",
        read="tenant:read",
        act="security:manage",
        link="/settings/security/mfa",
    ),
    StepDef(
        "invite",
        "organise",
        "Invite your team",
        read="members:read",
        act="members:invite",
        link="/settings/access/people?invite=1",
    ),
    StepDef(
        "functions",
        "organise",
        "Name who owns what",
        read="frameworks:read",
        act="controls:manage",
        link="/settings/organization/ownership",
    ),
    StepDef(
        "owners",
        "organise",
        "Assign control owners",
        read="frameworks:read",
        act="controls:manage",
        link="/controls?owner=unassigned",
    ),
    StepDef(
        "risks",
        "assess",
        "Assess your risks",
        read="risks:read",
        act="risks:manage",
        link="/risks",
    ),
    StepDef(
        "baseline",
        "assess",
        "Say what is already in place",
        read="frameworks:read",
        act="controls:manage",
        link="/quick-start/baseline",
    ),
    StepDef(
        "plan",
        "assess",
        "Approve your work plan",
        read="frameworks:read",
        act="controls:manage",
        link="/quick-start/plan",
    ),
    StepDef(
        "connect",
        "build",
        "Connect your systems",
        read="connectors:read",
        act="connectors:manage",
        link="/connectors",
    ),
    StepDef(
        "documents",
        "build",
        "Approve your policies and documents",
        read="documents:read",
        act="documents:manage",
        link="/documents/required",
    ),
    StepDef(
        "objectives",
        "build",
        "Meet what your auditor will check",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/objectives",
    ),
    StepDef(
        "evidence",
        "operate",
        "Collect evidence",
        read="frameworks:read",
        act="evidence:manage",
        link="/controls?evidence=none",
    ),
    StepDef(
        "failing",
        "operate",
        "Fix what is failing",
        read="frameworks:read",
        act="controls:manage",
        link="/controls?evidenced=automated",
    ),
    StepDef(
        "live",
        "operate",
        "Go live with your management system",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/scope?framework={framework}",
        each="applicability",
    ),
    StepDef(
        "description",
        "check",
        "Write your system description",
        read="frameworks:read",
        act="documents:manage",
        link="/frameworks/description",
        each="categories",
    ),
    StepDef(
        "internal_audit",
        "check",
        "Run your internal audit",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/assurance?framework={framework}",
        each="applicability",
    ),
    StepDef(
        "management_review",
        "check",
        "Hold your management review",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/assurance?framework={framework}",
        each="applicability",
    ),
    StepDef(
        "close_findings",
        "check",
        "Close findings",
        read="frameworks:read",
        act="controls:manage",
        link="/tasks",
    ),
    StepDef(
        "audit",
        "audit",
        "Record your audit",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/assurance?framework={framework}",
        each="any",
    ),
    StepDef(
        "next_cycle",
        "audit",
        "Plan your next period",
        read="frameworks:read",
        act="controls:manage",
        link="/frameworks/scope?framework={framework}",
        each="any",
    ),
)

STEP_KEYS: Final[frozenset[str]] = frozenset(step.key for step in STEPS)
