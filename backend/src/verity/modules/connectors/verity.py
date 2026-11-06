"""Verity's built-in checks: automated tests over data the workspace already keeps in Verity.

The built-in provider (``verity``) is the always-connected provider of the control framework
(ME-1). It reads no outside system. A run has the same three steps as GitHub's:

* ``collect`` reads each module's facts through that module's own service (rule 4), inside the
  tenant's session, into one typed ``Facts`` object. Every module rule that already exists
  (an SLA clock, a review date, a register's appetite, an acceptance's expiry) is reused as
  the module computes it, so a check never disagrees with the page a person reads.
* ``evaluate`` is pure: facts in, one ``Result`` per record out. Unit tested on its own.
* ``snapshot`` turns the facts into the JSON the evidence file carries, and
  ``evidence_snapshot`` keeps the part one check read.

Outcomes follow the connectors' rules. ``fail`` means the record does not meet the check. A
check with nothing to judge leaves no result, which the control page reads as "nothing to
verify" (not applicable), never as passing. Where "nothing exists" is itself the failure (no
policy at all, no risk assessment at all), the check says so with an explicit workspace fail.

People are judged by their membership: an owner is someone who can act, so an owner whose
membership is disabled, or who has not accepted the invitation yet, does not count.

Evidence a check relies on must have been filed by a person: Verity's own reports (``source``
set) are never counted as the thing they report on, or a check would satisfy itself.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Final

# The shared result shape: plain data, written as check_results rows by the service.
from verity.modules.connectors.github import Result

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from verity.modules.assets.service import AssetCheckFacts
    from verity.modules.compliance.control_service import ControlView
    from verity.modules.compliance.framework_service import DecisionFact
    from verity.modules.documents.service import AckFacts, DocumentFacts
    from verity.modules.evidence.service import PersonEvidence
    from verity.modules.risk.service import RegisterCheckFacts, RiskCheckFact
    from verity.modules.tasks.service import RemediationSla
    from verity.modules.vendors.service import VendorCheckFacts
    from verity.modules.vulnerabilities.service import SlaFinding

PROVIDER: Final = "verity"
EVALUATOR: Final = "verity.2026-10"
"""Stamped on every result, so a change to a rule is visible in the history."""

ISO: Final = "ISO27001"
WINDOW_MONTHS: Final = 12

# -- check keys --------------------------------------------------------------------

ASSETS_OWNER: Final = "verity.assets.owner_assigned"
ASSETS_CLASSIFIED: Final = "verity.assets.classified"
ASSETS_REVIEWED: Final = "verity.assets.reviewed"
ASSETS_DISPOSAL: Final = "verity.assets.disposal_recorded"
VULNS_SLA: Final = "verity.vulns.within_sla"
VULNS_KEV_OWNED: Final = "verity.vulns.kev_owned"
RISKS_REVIEWED: Final = "verity.risks.reviewed"
RISKS_TREATED: Final = "verity.risks.treated"
RISKS_CONTROLS: Final = "verity.risks.controls_linked"
RISKS_ACCEPTANCE: Final = "verity.risks.acceptance_current"
RISKS_ASSESSED: Final = "verity.risks.assessed_in_12_months"
VENDORS_OWNER_TIER: Final = "verity.vendors.owner_and_tier"
VENDORS_CADENCE: Final = "verity.vendors.assessed_in_cadence"
VENDORS_DPA: Final = "verity.vendors.dpa_on_file"
POLICIES_REVIEWED: Final = "verity.policies.reviewed"
POLICIES_ACKNOWLEDGED: Final = "verity.policies.acknowledged"
TASKS_SLA: Final = "verity.tasks.remediation_in_sla"
CONTROLS_OWNED: Final = "verity.controls.owned"
EVIDENCE_CURRENT: Final = "verity.evidence.current"
SOA_COMPLETE: Final = "verity.soa.complete"
ISMS_SCOPE_RECORDED: Final = "verity.isms.scope_recorded"
ISMS_SCOPE_DOCUMENTED: Final = "verity.isms.scope_documented"
CONTEXT_DOCUMENTED: Final = "verity.context.documented"
PARTIES_DOCUMENTED: Final = "verity.interested_parties.documented"
OBJECTIVES_DOCUMENTED: Final = "verity.objectives.documented"
COMMUNICATION_DOCUMENTED: Final = "verity.communication.plan_documented"
COMPETENCE_DOCUMENTED: Final = "verity.competence.documented"
DOCUMENTS_CONTROLLED: Final = "verity.documents.controlled"
INTERNAL_AUDIT: Final = "verity.audit.internal_in_12_months"
MANAGEMENT_REVIEW: Final = "verity.management_review.in_12_months"

#: A document check passes on a current document started from one of these templates, or
#: linked to one of the controls the check is mapped to.
DOCUMENT_TEMPLATES: Final[dict[str, tuple[str, ...]]] = {
    ISMS_SCOPE_DOCUMENTED: ("isms-scope-statement",),
    CONTEXT_DOCUMENTED: ("context-and-interested-parties",),
    PARTIES_DOCUMENTED: ("context-and-interested-parties",),
    OBJECTIVES_DOCUMENTED: ("security-objectives-plan",),
    COMMUNICATION_DOCUMENTED: ("security-communication-plan",),
    COMPETENCE_DOCUMENTED: ("competence-and-awareness-procedure",),
}

#: Checks answered by evidence a person filed on the check's control within the window.
EVIDENCE_IN_WINDOW: Final = (INTERNAL_AUDIT, MANAGEMENT_REVIEW)

#: Documents whose acknowledgement is always expected of staff, campaign or not.
ALWAYS_ACKNOWLEDGED: Final = ("code-of-conduct", "acceptable-use-policy")

IMPLEMENTED: Final[tuple[str, ...]] = (
    ASSETS_OWNER,
    ASSETS_CLASSIFIED,
    ASSETS_REVIEWED,
    ASSETS_DISPOSAL,
    VULNS_SLA,
    VULNS_KEV_OWNED,
    RISKS_REVIEWED,
    RISKS_TREATED,
    RISKS_CONTROLS,
    RISKS_ACCEPTANCE,
    RISKS_ASSESSED,
    VENDORS_OWNER_TIER,
    VENDORS_CADENCE,
    VENDORS_DPA,
    POLICIES_REVIEWED,
    POLICIES_ACKNOWLEDGED,
    TASKS_SLA,
    CONTROLS_OWNED,
    EVIDENCE_CURRENT,
    SOA_COMPLETE,
    ISMS_SCOPE_RECORDED,
    *DOCUMENT_TEMPLATES,
    DOCUMENTS_CONTROLLED,
    *EVIDENCE_IN_WINDOW,
)
"""Every check this provider evaluates. The content pack must list ``verity`` as an
implementation of exactly these (a unit test holds the two together)."""

_IN_SERVICE: Final = frozenset({"active", "in_maintenance"})
_OUT_OF_SERVICE: Final = frozenset({"decommissioned", "retired"})
#: Asset types that hold storage media, so disposal must say the media was sanitised.
_MEDIA_TYPES: Final = frozenset({"infrastructure", "data", "cloud"})
_URGENT_SEVERITIES: Final = frozenset({"critical", "high"})
_VENDOR_CLOSED: Final = frozenset({"terminated", "archived"})
_VENDOR_EXITING: Final = frozenset({"offboarding", "terminated", "archived"})
_VENDOR_IN_USE: Final = frozenset({"approved", "active", "flagged"})
_COVERED_TIERS: Final = frozenset({"critical", "high"})


# -- facts --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Member:
    name: str
    status: str


@dataclass(frozen=True, slots=True)
class ControlFact:
    """A live control of the workspace, as the checks need it."""

    id: uuid.UUID
    code: str
    name: str
    status: str
    owner_membership_id: uuid.UUID | None
    template_id: uuid.UUID | None
    frameworks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IsoScope:
    added: bool
    engagement_id: uuid.UUID | None
    engagement_name: str | None
    scope_statement: str | None
    framework_id: uuid.UUID | None
    framework_name: str


@dataclass(frozen=True, slots=True)
class Facts:
    """Everything one run judges, read at one instant."""

    tenant_id: uuid.UUID
    now: datetime
    members: dict[uuid.UUID, Member]
    active_frameworks: tuple[str, ...]
    controls: tuple[ControlFact, ...]
    check_controls: dict[str, tuple[ControlFact, ...]]
    with_current_evidence: frozenset[uuid.UUID]
    with_any_evidence: frozenset[uuid.UUID]
    person_evidence: dict[uuid.UUID, tuple[PersonEvidence, ...]]
    assets: tuple[AssetCheckFacts, ...]
    findings: tuple[SlaFinding, ...]
    vendors: tuple[VendorCheckFacts, ...]
    vendor_cadence_days: dict[str, int]
    registers: tuple[RegisterCheckFacts, ...]
    documents: tuple[DocumentFacts, ...]
    acknowledgements: dict[uuid.UUID, AckFacts]
    remediation: tuple[RemediationSla, ...]
    soa: tuple[uuid.UUID, str, tuple[DecisionFact, ...]] | None
    iso_scope: IsoScope
    #: Members who hold access only through an engagement (guest auditors).
    guests: frozenset[uuid.UUID] = frozenset()
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def today(self) -> date:
        return self.now.astimezone(UTC).date()


async def collect(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    now: datetime,
    check_templates: Mapping[str, Iterable[uuid.UUID]],
) -> Facts:
    """Read every module's facts for one run, through each module's service.

    ``check_templates`` maps a check key to the control templates it is mapped to; the
    workspace controls adopted from those templates are the check's controls.
    """
    from verity.modules.assets.service import asset_service  # noqa: PLC0415
    from verity.modules.compliance.control_service import control_service  # noqa: PLC0415
    from verity.modules.compliance.engagement_service import (  # noqa: PLC0415
        engagement_service,
    )
    from verity.modules.compliance.framework_service import framework_service  # noqa: PLC0415
    from verity.modules.documents.service import document_service  # noqa: PLC0415
    from verity.modules.evidence.service import evidence_service  # noqa: PLC0415
    from verity.modules.iam.service import iam_service  # noqa: PLC0415
    from verity.modules.risk.service import risk_service  # noqa: PLC0415
    from verity.modules.tasks.service import task_service  # noqa: PLC0415
    from verity.modules.vendors.service import vendor_service  # noqa: PLC0415
    from verity.modules.vulnerabilities.service import vulnerability_service  # noqa: PLC0415

    today = now.astimezone(UTC).date()
    members = {
        m.membership_id: Member(name=m.full_name, status=m.status)
        for m in await iam_service.list_members(session, tenant_id=tenant_id)
    }
    added = tuple(
        sorted(
            view.code
            for view in await framework_service.list_for_tenant(session, tenant_id=tenant_id)
            if view.added
        )
    )
    # A workspace with no framework recorded is a SOC 2 workspace (the adoption rule).
    active_frameworks = added or ("SOC2",)
    views: Sequence[ControlView] = await control_service.list_controls(session, tenant_id=tenant_id)
    controls = tuple(
        ControlFact(
            id=view.id,
            code=view.code,
            name=view.name,
            status=view.status,
            owner_membership_id=view.owner_membership_id,
            template_id=view.template_id,
            frameworks=tuple(sorted({key.split(":", 1)[0] for key in view.requirement_keys})),
        )
        for view in views
        if view.disabled_at is None
    )
    by_template = {c.template_id: c for c in controls if c.template_id is not None}
    check_controls = {
        key: tuple(
            sorted((by_template[t] for t in templates if t in by_template), key=lambda c: c.code)
        )
        for key, templates in check_templates.items()
    }
    evidence_controls = [c.id for key in EVIDENCE_IN_WINDOW for c in check_controls.get(key, ())]
    person = await evidence_service.person_evidence(
        session, tenant_id, control_ids=evidence_controls
    )
    vendors, cadence = await vendor_service.check_facts(session, tenant_id=tenant_id)
    decisions = await framework_service.applicability_decisions(
        session, tenant_id=tenant_id, framework_code=ISO
    )
    context = await engagement_service.context(session, tenant_id=tenant_id, framework_code=ISO)
    engagement = context.engagement if context is not None else None
    iso_scope = IsoScope(
        added=bool(context is not None and context.scope_set),
        engagement_id=engagement.id if engagement is not None else None,
        engagement_name=engagement.name if engagement is not None else None,
        scope_statement=engagement.scope_statement if engagement is not None else None,
        framework_id=context.framework.id if context is not None else None,
        framework_name=context.framework.name if context is not None else "ISO 27001",
    )
    return Facts(
        tenant_id=tenant_id,
        now=now,
        members=members,
        active_frameworks=active_frameworks,
        controls=controls,
        check_controls=check_controls,
        with_current_evidence=frozenset(
            await evidence_service.control_ids_with_current_evidence(
                session,
                tenant_id,
                today=today,
                exclude_source=PROVIDER,
                undated_since=_months_before(today, WINDOW_MONTHS),
            )
        ),
        with_any_evidence=frozenset(
            await evidence_service.control_ids_with_evidence(
                session, tenant_id, exclude_source=PROVIDER
            )
        ),
        person_evidence={key: tuple(value) for key, value in person.items()},
        assets=tuple(await asset_service.check_facts(session, tenant_id=tenant_id)),
        findings=tuple(
            await vulnerability_service.sla_findings(session, tenant_id=tenant_id, now=now)
        ),
        vendors=tuple(vendors),
        vendor_cadence_days=cadence,
        registers=tuple(await risk_service.check_facts(session, tenant_id=tenant_id)),
        documents=tuple(
            await document_service.check_facts(session, tenant_id=tenant_id, today=today)
        ),
        acknowledgements=await document_service.acknowledgement_facts(
            session, tenant_id=tenant_id, now=now
        ),
        remediation=tuple(
            await task_service.remediation_sla(session, tenant_id=tenant_id, now=now)
        ),
        soa=(decisions[0], decisions[1], tuple(decisions[2])) if decisions else None,
        iso_scope=iso_scope,
        guests=frozenset(await iam_service.guest_membership_ids(session, tenant_id=tenant_id)),
    )


# -- helpers --------------------------------------------------------------------------


def _months_before(day: date, months: int) -> date:
    """``day`` minus whole months, clipped to the end of a shorter month."""
    from verity.modules.documents.schedule import add_months  # noqa: PLC0415

    return add_months(day, -months)


def _result(  # noqa: PLR0913, PLR0917 — one result: what, which record, the verdict, its reasons
    check: str,
    resource_type: str,
    resource_id: object,
    name: str,
    outcome: str,
    summary: str,
    *,
    reason: str | None = None,
    url: str | None = None,
    **facts: object,
) -> Result:
    detail: dict[str, Any] = {"summary": summary, "rule": EVALUATOR}
    if reason is not None:
        detail["reason"] = reason
    if url is not None:
        detail["url"] = url
    detail.update({key: _plain(value) for key, value in facts.items()})
    return Result(
        check_key=check,
        resource_type=resource_type,
        resource_id=str(resource_id),
        resource_name=name,
        outcome=outcome,
        detail=detail,
    )


def _owner_gap(facts: Facts, membership_id: uuid.UUID | None) -> tuple[str, str] | None:
    """Why this owner cannot be counted, as (reason, sentence), or None when they can."""
    if membership_id is None:
        return "no_owner", "No owner is set."
    member = facts.members.get(membership_id)
    if member is None:
        return "owner_not_member", "The owner is no longer a member of this workspace."
    if member.status == "disabled":
        return "owner_inactive", f"The owner, {member.name}, has been removed from the workspace."
    if member.status != "active":
        return "owner_inactive", f"The owner, {member.name}, has not accepted the invitation yet."
    return None


def _owner_name(facts: Facts, membership_id: uuid.UUID | None) -> str | None:
    member = facts.members.get(membership_id) if membership_id else None
    return member.name if member else None


def _active(facts: Facts, ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    return {i for i in ids if (m := facts.members.get(i)) is not None and m.status == "active"}


def _fmt(day: date | datetime | None) -> str:
    if day is None:
        return "no date"
    if isinstance(day, datetime):
        day = day.astimezone(UTC).date()
    return f"{day.day} {day:%b %Y}"


# -- evaluation ---------------------------------------------------------------------


def evaluate(facts: Facts) -> list[Result]:
    """Every result of one run. Pure: the same facts always give the same results."""
    results: list[Result] = []
    for rule in (
        _assets,
        _vulnerabilities,
        _risks,
        _vendors,
        _policies,
        _acknowledgements,
        _document_checks,
        _documents_controlled,
        _remediation,
        _controls,
        _statement_of_applicability,
        _iso_scope,
        _evidence_in_window,
    ):
        results.extend(rule(facts))
    return results


def _assets(facts: Facts) -> list[Result]:
    out: list[Result] = []
    for a in facts.assets:
        url = f"/assets/{a.id}"
        base: dict[str, Any] = {
            "status": a.status,
            "asset_type": a.asset_type,
            "host": a.host,
            "tier": a.tier,
        }
        if a.status in _IN_SERVICE:
            gap = _owner_gap(facts, a.primary_owner_membership_id)
            owner = _owner_name(facts, a.primary_owner_membership_id)
            out.append(
                _result(
                    ASSETS_OWNER,
                    "asset",
                    a.id,
                    a.name,
                    "fail" if gap else "pass",
                    gap[1] if gap else f"Owned by {owner}.",
                    reason=gap[0] if gap else None,
                    url=url,
                    owner=owner,
                    **base,
                )
            )
            out.append(
                _result(
                    ASSETS_CLASSIFIED,
                    "asset",
                    a.id,
                    a.name,
                    "pass" if a.data_classification else "fail",
                    f"Classified {a.data_classification}."
                    if a.data_classification
                    else "No data classification is set.",
                    reason=None if a.data_classification else "no_classification",
                    url=url,
                    data_classification=a.data_classification,
                    regulated_data_type=a.regulated_data_type,
                    compliance_scope=list(a.compliance_scope),
                    **base,
                )
            )
            due = (
                a.last_reviewed_at + timedelta(days=a.review_days)
                if a.last_reviewed_at is not None
                else None
            )
            if a.last_reviewed_at is None:
                outcome, summary, reason = "fail", "It has never been reviewed.", "never_reviewed"
            elif facts.now - a.last_reviewed_at > timedelta(days=a.review_days):
                outcome, reason = "fail", "review_overdue"
                summary = f"Review was due {_fmt(due)} (every {a.review_days} days)."
            else:
                outcome, reason = "pass", None
                summary = f"Reviewed {_fmt(a.last_reviewed_at)}; next due {_fmt(due)}."
            out.append(
                _result(
                    ASSETS_REVIEWED,
                    "asset",
                    a.id,
                    a.name,
                    outcome,
                    summary,
                    reason=reason,
                    url=url,
                    last_reviewed_at=a.last_reviewed_at,
                    review_days=a.review_days,
                    due_at=due,
                    **base,
                )
            )
        elif a.status in _OUT_OF_SERVICE:
            out.append(_disposal(a, url, base))
    return out


def _disposal(a: AssetCheckFacts, url: str, base: dict[str, Any]) -> Result:
    record = a.disposal
    if record is None:
        if a.status == "retired" and a.retired_from == "planned":
            return _result(
                ASSETS_DISPOSAL,
                "asset",
                a.id,
                a.name,
                "not_applicable",
                "Retired before it was ever in service, so nothing was disposed of.",
                reason="never_in_service",
                url=url,
                **base,
            )
        return _result(
            ASSETS_DISPOSAL,
            "asset",
            a.id,
            a.name,
            "fail",
            "Taken out of service with no disposal record.",
            reason="no_disposal_record",
            url=url,
            **base,
        )
    facts_of: dict[str, Any] = {
        "disposal_method": record.disposal_method,
        "media_sanitised": record.media_sanitised,
        "evidence_ref": record.evidence_ref,
        "decommissioned_at": record.decommissioned_at,
    }
    if not record.disposal_method.strip():
        return _result(
            ASSETS_DISPOSAL,
            "asset",
            a.id,
            a.name,
            "fail",
            "The disposal record does not say how the asset was disposed of.",
            reason="no_disposal_method",
            url=url,
            **base,
            **facts_of,
        )
    if (
        a.asset_type in _MEDIA_TYPES
        and not record.media_sanitised
        and record.disposal_method != "physically_destroyed"
    ):
        return _result(
            ASSETS_DISPOSAL,
            "asset",
            a.id,
            a.name,
            "fail",
            "Disposed of without a record that its storage was wiped or destroyed.",
            reason="media_not_sanitised",
            url=url,
            **base,
            **facts_of,
        )
    method = record.disposal_method.replace("_", " ")
    return _result(
        ASSETS_DISPOSAL,
        "asset",
        a.id,
        a.name,
        "pass",
        f"Disposed of ({method}) on {_fmt(record.decommissioned_at)}.",
        url=url,
        **base,
        **facts_of,
    )


def _finding_name(f: SlaFinding) -> str:
    name = f"{f.cve_id or f.title} on {f.asset_name}"
    return f"{name} ({f.locator})" if f.locator else name


def _vulnerabilities(facts: Facts) -> list[Result]:
    out: list[Result] = []
    for f in facts.findings:
        url = f"/vulnerabilities/{f.instance_id}"
        base: dict[str, Any] = {
            "severity": f.severity,
            "state": f.state,
            "sla_due_at": f.sla_due_at,
            "first_detected_at": f.first_detected_at,
            "accepted_expires_at": f.accepted_expires_at,
            "owner_membership_id": f.owner_membership_id,
            "kev": f.kev_flag,
        }
        if f.severity in _URGENT_SEVERITIES and (f.effectively_open or f.waiver_live):
            if f.waiver_live:
                outcome, reason = "pass", "risk_accepted"
                summary = f"Risk accepted until {_fmt(f.accepted_expires_at)}."
            elif f.sla_due_at is None:
                outcome, reason = "fail", "no_sla_date"
                summary = "No SLA due date is recorded for this critical or high finding."
            elif f.past_sla:
                outcome, reason = "fail", "past_sla"
                days = (facts.now - f.sla_due_at).days
                summary = f"{days} days past its SLA (due {_fmt(f.sla_due_at)})."
                if f.state == "accepted":
                    summary += f" Its risk acceptance expired on {_fmt(f.accepted_expires_at)}."
            else:
                outcome, reason = "pass", None
                summary = f"Open, due {_fmt(f.sla_due_at)}."
            out.append(
                _result(
                    VULNS_SLA,
                    "finding",
                    f.instance_id,
                    _finding_name(f),
                    outcome,
                    summary,
                    reason=reason,
                    url=url,
                    **base,
                )
            )
        if f.kev_flag and f.effectively_open:
            gap = _owner_gap(facts, f.owner_membership_id)
            out.append(
                _result(
                    VULNS_KEV_OWNED,
                    "finding",
                    f.instance_id,
                    _finding_name(f),
                    "fail" if gap else "pass",
                    (
                        "This known exploited finding has no one able to act on it. " + gap[1]
                        if gap
                        else f"Owned by {_owner_name(facts, f.owner_membership_id)}."
                    ),
                    reason=gap[0] if gap else None,
                    url=url,
                    **base,
                )
            )
    return out


def _risks(facts: Facts) -> list[Result]:  # noqa: PLR0912, PLR0915 — five checks over each register
    out: list[Result] = []
    judged_registers = 0
    today = facts.today
    year_ago = facts.now - timedelta(days=365)
    for register in facts.registers:
        if register.status != "active":
            continue
        assessed_ok = True
        unscored: list[str] = []
        stale: list[str] = []
        for r in register.risks:
            name = f"{r.code} {r.title}"
            url = f"/risks/{r.risk_id}"
            base: dict[str, Any] = {
                "register": register.name,
                "status": r.status,
                "treatment": r.treatment,
                "score": r.effective_score,
                "band": r.effective_band,
                "appetite_status": r.appetite_status,
            }
            # Reviewed on schedule (the register's own review date).
            if r.next_review_on is None:
                verdict: tuple[str, str, str | None]
                verdict = ("fail", "No next review date is set.", "no_review_date")
            elif r.next_review_on < today:
                verdict = (
                    "fail",
                    f"Review was due {_fmt(r.next_review_on)}.",
                    "review_overdue",
                )
            else:
                verdict = ("pass", f"Next review {_fmt(r.next_review_on)}.", None)
            out.append(
                _result(
                    RISKS_REVIEWED,
                    "risk",
                    r.risk_id,
                    name,
                    verdict[0],
                    verdict[1],
                    reason=verdict[2],
                    url=url,
                    next_review_on=r.next_review_on,
                    last_reviewed_at=r.last_reviewed_at,
                    review_cadence_days=register.review_cadence_days,
                    **base,
                )
            )
            out.append(_treated(facts, r, register, name, url, base))
            # Mitigated risks link to the controls that mitigate them.
            if r.status != "accepted" and (
                r.treatment == "mitigate" or (r.treatment is None and r.status == "mitigated")
            ):
                out.append(
                    _result(
                        RISKS_CONTROLS,
                        "risk",
                        r.risk_id,
                        name,
                        "pass" if r.control_count else "fail",
                        f"Linked to {r.control_count} control(s)."
                        if r.control_count
                        else "Treated by mitigation, but linked to no control.",
                        reason=None if r.control_count else "no_controls",
                        url=url,
                        control_count=r.control_count,
                        **base,
                    )
                )
            # Acceptances in force.
            if r.status == "accepted":
                if r.acceptance_status != "active" or r.acceptance_expires_on is None:
                    verdict = (
                        "fail",
                        "Marked accepted, but no acceptance is in force.",
                        "no_acceptance_in_force",
                    )
                elif r.acceptance_expires_on < today:
                    verdict = (
                        "fail",
                        f"The acceptance expired on {_fmt(r.acceptance_expires_on)}.",
                        "expired",
                    )
                else:
                    verdict = (
                        "pass",
                        f"Accepted until {_fmt(r.acceptance_expires_on)}.",
                        None,
                    )
                out.append(
                    _result(
                        RISKS_ACCEPTANCE,
                        "risk",
                        r.risk_id,
                        name,
                        verdict[0],
                        verdict[1],
                        reason=verdict[2],
                        url=url,
                        acceptance_expires_on=r.acceptance_expires_on,
                        approver=_owner_name(facts, r.acceptance_approver_membership_id),
                        **base,
                    )
                )
            if r.inherent_score is None:
                unscored.append(r.code)
                assessed_ok = False
            elif r.last_assessed_at is None or r.last_assessed_at < year_ago:
                stale.append(r.code)
                assessed_ok = False
        # Assessed in the last 12 months, per register: every live risk scored and assessed.
        if not register.risks:
            out.append(
                _result(
                    RISKS_ASSESSED,
                    "risk_register",
                    register.register_id,
                    register.name,
                    "not_applicable",
                    "No open risks in this register.",
                    reason="no_risks",
                )
            )
            continue
        judged_registers += 1
        latest = max(
            (r.last_assessed_at for r in register.risks if r.last_assessed_at),
            default=None,
        )
        if assessed_ok:
            summary = f"All {len(register.risks)} risks assessed in the last 12 months."
        else:
            parts = []
            if unscored:
                parts.append(f"{len(unscored)} not scored ({', '.join(unscored[:10])})")
            if stale:
                parts.append(f"{len(stale)} not assessed in 12 months ({', '.join(stale[:10])})")
            summary = "; ".join(parts) + "."
        out.append(
            _result(
                RISKS_ASSESSED,
                "risk_register",
                register.register_id,
                register.name,
                "pass" if assessed_ok else "fail",
                summary,
                reason=None if assessed_ok else ("unscored_risks" if unscored else "stale_risks"),
                live_risks=len(register.risks),
                latest_assessment_at=latest,
                unscored=unscored,
                stale=stale,
            )
        )
    if not judged_registers:
        out.append(
            _result(
                RISKS_ASSESSED,
                "workspace",
                facts.tenant_id,
                "Risk registers",
                "fail",
                "No risk assessment is recorded: no active register holds an open risk.",
                reason="no_assessment_recorded",
            )
        )
    return out


def _treated(  # noqa: PLR0913, PLR0917 — one risk and the register it is judged against
    facts: Facts,
    r: RiskCheckFact,
    register: RegisterCheckFacts,
    name: str,
    url: str,
    base: dict[str, Any],
) -> Result:
    """Risks above the acceptance criteria have an owner and a decided treatment.

    Above means outside the register's appetite for the risk's category (tolerated or
    breach). Where the category has no appetite, any band above the register's lowest.
    """
    if r.inherent_score is None:
        return _result(
            RISKS_TREATED,
            "risk",
            r.risk_id,
            name,
            "fail",
            "Not scored, so it cannot be shown to be within the acceptance criteria.",
            reason="unscored",
            url=url,
            **base,
        )
    if r.appetite_status is not None:
        above = r.appetite_status in ("tolerated", "breach")
    else:
        above = r.effective_band is not None and r.effective_band != register.lowest_band
    if not above:
        return _result(
            RISKS_TREATED,
            "risk",
            r.risk_id,
            name,
            "not_applicable",
            "Within the acceptance criteria.",
            reason="within_appetite",
            url=url,
            **base,
        )
    gap = _owner_gap(facts, r.owner_membership_id)
    if gap is not None:
        return _result(
            RISKS_TREATED, "risk", r.risk_id, name, "fail", gap[1], reason=gap[0], url=url, **base
        )
    if r.treatment is None:
        return _result(
            RISKS_TREATED,
            "risk",
            r.risk_id,
            name,
            "fail",
            "Above the acceptance criteria with no treatment decided.",
            reason="no_treatment",
            url=url,
            **base,
        )
    if r.treatment == "accept" and (
        r.status != "accepted"
        or r.acceptance_status != "active"
        or r.acceptance_expires_on is None
        or r.acceptance_expires_on < facts.today
    ):
        return _result(
            RISKS_TREATED,
            "risk",
            r.risk_id,
            name,
            "fail",
            "The treatment is to accept it, but no acceptance is in force.",
            reason="acceptance_not_in_force",
            url=url,
            **base,
        )
    return _result(
        RISKS_TREATED,
        "risk",
        r.risk_id,
        name,
        "pass",
        f"Owned by {_owner_name(facts, r.owner_membership_id)}; treatment: {r.treatment}.",
        url=url,
        **base,
    )


def _vendors(facts: Facts) -> list[Result]:  # noqa: PLR0912 — three checks per vendor
    out: list[Result] = []
    today = facts.today
    for v in facts.vendors:
        url = f"/vendors/{v.id}"
        base: dict[str, Any] = {"lifecycle_status": v.lifecycle_status, "tier": v.tier}
        if v.lifecycle_status not in _VENDOR_CLOSED:
            gaps: list[str] = []
            gap = _owner_gap(facts, v.business_owner_membership_id)
            if gap:
                gaps.append(gap[1])
            if v.tier is None:
                gaps.append("It is not tiered.")
            untiered = [
                e.name for e in v.engagements if e.status not in _VENDOR_EXITING and e.tier is None
            ]
            if untiered:
                gaps.append(f"Engagement not tiered: {', '.join(untiered)}.")
            out.append(
                _result(
                    VENDORS_OWNER_TIER,
                    "vendor",
                    v.id,
                    v.name,
                    "fail" if gaps else "pass",
                    " ".join(gaps)
                    if gaps
                    else f"Owned by {_owner_name(facts, v.business_owner_membership_id)}, "
                    f"tier {v.tier}.",
                    reason=(gap[0] if gap else "not_tiered") if gaps else None,
                    url=url,
                    untiered_engagements=untiered,
                    **base,
                )
            )
        if v.lifecycle_status not in _VENDOR_EXITING:
            counted = [
                e
                for e in v.engagements
                if e.tier in _COVERED_TIERS
                and e.status not in _VENDOR_EXITING
                and (e.last_review_completed_at is not None or e.status in _VENDOR_IN_USE)
            ]
            if not counted:
                out.append(
                    _result(
                        VENDORS_CADENCE,
                        "vendor",
                        v.id,
                        v.name,
                        "not_applicable",
                        "No critical or high engagement in use, so no reassessment cadence "
                        "applies.",
                        reason="not_covered",
                        url=url,
                        **base,
                    )
                )
            else:
                problems: list[str] = []
                if v.next_reassessment_on is None:
                    problems.append("No reassessment is booked.")
                elif v.next_reassessment_on < today:
                    problems.append(f"Reassessment was due {_fmt(v.next_reassessment_on)}.")
                for e in counted:
                    days = facts.vendor_cadence_days.get(e.tier or "", 365)
                    if e.last_review_completed_at is None:
                        problems.append(f"{e.name} is in use with no completed review.")
                    elif e.last_review_completed_at.astimezone(UTC).date() < today - timedelta(
                        days=days
                    ):
                        problems.append(
                            f"{e.name} was last reviewed {_fmt(e.last_review_completed_at)}, "
                            f"beyond its {days} day cadence."
                        )
                out.append(
                    _result(
                        VENDORS_CADENCE,
                        "vendor",
                        v.id,
                        v.name,
                        "fail" if problems else "pass",
                        " ".join(problems)
                        if problems
                        else f"Next reassessment {_fmt(v.next_reassessment_on)}.",
                        reason="overdue" if problems else None,
                        url=url,
                        next_reassessment_on=v.next_reassessment_on,
                        engagements=[
                            {
                                "name": e.name,
                                "tier": e.tier,
                                "last_review_completed_at": e.last_review_completed_at,
                            }
                            for e in counted
                        ],
                        **base,
                    )
                )
        if v.lifecycle_status not in _VENDOR_CLOSED:
            out.append(_dpa(v, url, base, today))
    return out


def _dpa(v: VendorCheckFacts, url: str, base: dict[str, Any], today: date) -> Result:
    data: dict[str, Any] = {
        "stores_pii": v.stores_pii,
        "data_types_in_scope": list(v.data_types_in_scope),
        "data_classification": v.data_classification,
        "dpas": [
            {
                "kind": d.kind,
                "title": d.title,
                "status": d.status,
                "valid_until": d.valid_until,
                "evidence_attached": d.evidence_attached,
            }
            for d in v.dpas
        ],
    }
    if not v.stores_pii:
        return _result(
            VENDORS_DPA,
            "vendor",
            v.id,
            v.name,
            "not_applicable",
            "Not marked as holding personal data.",
            reason="no_personal_data",
            url=url,
            **base,
            **data,
        )
    # In use, the same rule as the reassessment check: approved through review, or a vendor
    # or engagement already approved, active or flagged.
    if not (
        v.lifecycle_status in _VENDOR_IN_USE
        or any(
            e.last_review_completed_at is not None or e.status in _VENDOR_IN_USE
            for e in v.engagements
        )
    ):
        return _result(
            VENDORS_DPA,
            "vendor",
            v.id,
            v.name,
            "not_applicable",
            "Not approved for use yet; the agreement is checked once it is.",
            reason="not_approved",
            url=url,
            **base,
            **data,
        )
    in_force = [
        d
        for d in v.dpas
        if (d.valid_until is None or d.valid_until >= today)
        and (
            (d.kind == "document" and d.status in ("received", "reviewed"))
            or (d.kind == "contract" and d.status == "active")
        )
    ]
    attached = [d for d in in_force if d.evidence_attached]
    if attached:
        return _result(
            VENDORS_DPA,
            "vendor",
            v.id,
            v.name,
            "pass",
            f"Data processing agreement on file: {attached[0].title}.",
            url=url,
            **base,
            **data,
        )
    if in_force:
        summary, reason = (
            "A data processing agreement is recorded as in force, but no copy is attached.",
            "dpa_not_attached",
        )
    elif not v.dpas:
        summary, reason = "Holds personal data with no data processing agreement.", "no_dpa"
    elif any(d.valid_until is not None and d.valid_until < today for d in v.dpas):
        summary, reason = "The data processing agreement has expired.", "dpa_expired"
    else:
        summary, reason = (
            "A data processing agreement is requested or in draft, not in force.",
            ("dpa_not_in_force"),
        )
    return _result(
        VENDORS_DPA, "vendor", v.id, v.name, "fail", summary, reason=reason, url=url, **base, **data
    )


_GAP_SENTENCES: Final = {
    "not_published": "It is not published.",
    "no_review_date": "It has no review date.",
    "review_overdue": "Its review date has passed.",
    "no_approval": "It has no approval on record.",
    "approval_older_than_interval": "It was last approved more than 12 months ago.",
}


def _required(facts: Facts) -> list[DocumentFacts]:
    """Documents the workspace relies on: started from a shipped template, or linked to a
    live control. Archived documents never reach here."""
    live = {c.id for c in facts.controls}
    return [d for d in facts.documents if d.template_key or any(c in live for c in d.control_ids)]


def _doc_gap(d: DocumentFacts) -> tuple[str, str] | None:
    if d.gap is not None:
        return d.gap, _GAP_SENTENCES.get(d.gap, d.gap)
    if d.open_placeholders:
        return (
            "unfilled_placeholders",
            f"It still has {d.open_placeholders} placeholder(s) to fill in.",
        )
    return None


def _policies(facts: Facts) -> list[Result]:
    required = _required(facts)
    if not required:
        return [
            _result(
                POLICIES_REVIEWED,
                "library",
                facts.tenant_id,
                "Policy library",
                "fail",
                "No policy is started from a template or linked to a control.",
                reason="no_policies",
                url="/documents",
            )
        ]
    out: list[Result] = []
    for d in required:
        gap = _doc_gap(d)
        out.append(
            _result(
                POLICIES_REVIEWED,
                "document",
                d.id,
                f"{d.code} {d.title}",
                "fail" if gap else "pass",
                gap[1] if gap else f"Published and current; next review {_fmt(d.renewal_date)}.",
                reason=gap[0] if gap else None,
                url=f"/documents/{d.id}",
                lifecycle=d.lifecycle,
                renewal_date=d.renewal_date,
                approved_at=d.approved_at,
                version=d.current_version_no,
            )
        )
    return out


def _acknowledgements(facts: Facts) -> list[Result]:
    """Staff signed the current text of the documents they must acknowledge.

    The code of conduct, the acceptable use policy and any document linked to this check's
    controls bind every member of staff (active members who are not guest auditors), so
    the population is the staff, not whoever a campaign named. Any other document is
    judged over the people its current campaigns asked.
    """
    out: list[Result] = []
    controls = {c.id for c in facts.check_controls.get(POLICIES_ACKNOWLEDGED, ())}
    staff = _active(facts, facts.members) - facts.guests
    for d in _required(facts):
        if d.lifecycle != "published":
            continue
        ack = facts.acknowledgements.get(d.id)
        name = f"{d.code} {d.title}"
        url = f"/documents/{d.id}"
        always = d.template_key in ALWAYS_ACKNOWLEDGED or bool(controls & set(d.control_ids))
        asked_now = _active(facts, ack.asked_current) if ack else set()
        signed_any = _active(facts, ack.signed_current | ack.signed_direct) if ack else set()
        if always:
            population = staff
            missing = population - signed_any - asked_now
            if missing:
                never = ack is None or ack.campaigns == 0
                names = sorted(facts.members[i].name for i in missing)
                out.append(
                    _result(
                        POLICIES_ACKNOWLEDGED,
                        "document",
                        d.id,
                        name,
                        "fail",
                        "Staff have never been asked to acknowledge it."
                        if never and not signed_any
                        else f"{len(missing)} of {len(population)} people have not been asked "
                        f"to acknowledge the current version: {', '.join(names[:10])}.",
                        reason="never_sent" if never and not signed_any else "not_asked",
                        url=url,
                        expected=len(population),
                        missing=len(missing),
                    )
                )
                continue
        else:
            population = asked_now
            if not population:
                if ack is not None and ack.campaigns:
                    out.append(
                        _result(
                            POLICIES_ACKNOWLEDGED,
                            "document",
                            d.id,
                            name,
                            "not_applicable",
                            "Republished since it was last sent; not sent for the current "
                            "version yet.",
                            reason="not_sent_for_current_version",
                            url=url,
                        )
                    )
                continue
        if not population:
            continue
        signed = signed_any & population
        late = (_active(facts, ack.late) if ack else set()) & population
        counts: dict[str, Any] = {
            "asked": len(population),
            "signed": len(signed),
            "late": len(late),
        }
        if late:
            names = sorted(facts.members[i].name for i in late)
            outcome, reason = "fail", "late"
            summary = (
                f"{len(late)} of {len(population)} people are late to acknowledge the current "
                f"version: {', '.join(names[:10])}."
            )
        elif signed:
            outcome, reason = "pass", None
            summary = (
                f"{len(signed)} of {len(population)} people acknowledged the current version; "
                "nobody is late."
            )
        else:
            outcome, reason = "not_applicable", "in_progress"
            due = ack.next_due_at if ack else None
            summary = f"Acknowledgement in progress, due {_fmt(due)}."
        out.append(
            _result(
                POLICIES_ACKNOWLEDGED,
                "document",
                d.id,
                name,
                outcome,
                summary,
                reason=reason,
                url=url,
                **counts,
            )
        )
    return out


def _document_checks(facts: Facts) -> list[Result]:
    """One result per check: a current document for the check's control, or why not."""
    out: list[Result] = []
    for check, templates in DOCUMENT_TEMPLATES.items():
        controls = [c for c in facts.check_controls.get(check, ()) if c.status != "not_applicable"]
        if not controls:
            continue
        control = controls[0]
        ids = {c.id for c in controls}
        candidates = [
            d for d in facts.documents if d.template_key in templates or ids & set(d.control_ids)
        ]
        current = [d for d in candidates if _doc_gap(d) is None]
        listed = [
            {
                "code": d.code,
                "title": d.title,
                "version": d.current_version_no,
                "gap": (_doc_gap(d) or (None, None))[0],
            }
            for d in candidates
        ]
        if current:
            outcome, reason = "pass", None
            summary = f"In force: {current[0].code} {current[0].title}."
        elif candidates:
            outcome, reason = "fail", "not_current"
            first = candidates[0]
            summary = (
                f"{first.code} {first.title} is not in force. {(_doc_gap(first) or ('', ''))[1]}"
            )
        else:
            outcome, reason = "fail", "missing"
            summary = "No document for this is in the library."
        out.append(
            _result(
                check,
                "control",
                control.id,
                f"{control.code} {control.name}",
                outcome,
                summary,
                reason=reason,
                url=f"/controls/{control.id}",
                documents=listed,
            )
        )
    return out


def _documents_controlled(facts: Facts) -> list[Result]:
    out: list[Result] = []
    for d in facts.documents:
        if d.lifecycle != "published":
            continue
        gaps: list[str] = []
        reasons: list[str] = []
        owner = _owner_gap(facts, d.owner_membership_id)
        if owner:
            reasons.append(owner[0])
            gaps.append(owner[1])
        approved = (
            d.approved_at is not None
            and bool(d.tiers)
            and all(status == "approved" and decided for _tier, status, decided in d.tiers)
            and bool(d.approver_ids)
        )
        if not approved:
            reasons.append("no_approval_record")
            gaps.append("Its approval is not on record for every tier.")
        elif (
            d.current_version_created_at is not None
            and d.approved_at is not None
            and d.current_version_created_at > d.approved_at
        ):
            reasons.append("approval_predates_current_version")
            gaps.append("The current text was saved after it was approved.")
        # The documents module's currency rule, so the two document checks agree: an
        # approval older than the review interval is stale however far out the review
        # date was moved. ``no_approval`` is covered by the tier test above.
        if d.gap in ("no_review_date", "review_overdue", "approval_older_than_interval"):
            reasons.append(d.gap)
            gaps.append(
                f"Its review was due {_fmt(d.renewal_date)}."
                if d.gap == "review_overdue"
                else _GAP_SENTENCES[d.gap]
            )
        out.append(
            _result(
                DOCUMENTS_CONTROLLED,
                "document",
                d.id,
                f"{d.code} {d.title}",
                "fail" if gaps else "pass",
                " ".join(gaps)
                if gaps
                else f"Owned, approved and current (version {d.current_version_no}).",
                reason=reasons[0] if reasons else None,
                url=f"/documents/{d.id}",
                reasons=reasons,
                version=d.current_version_no,
                approved_at=d.approved_at,
                renewal_date=d.renewal_date,
                approved_by_author=bool(
                    d.current_version_author_id and d.current_version_author_id in d.approver_ids
                ),
            )
        )
    return out


def _remediation(facts: Facts) -> list[Result]:
    out: list[Result] = []
    for t in facts.remediation:
        name = f"{t.code} {t.title}"
        base: dict[str, Any] = {
            "status": t.status,
            "sla_level": t.sla_level,
            "deadline": t.deadline,
            "deadline_from": t.deadline_from,
            "linked_to": list(t.linked_to),
        }
        if t.deadline is None or t.state == "none":
            out.append(
                _result(
                    TASKS_SLA,
                    "task",
                    t.task_id,
                    name,
                    "not_applicable",
                    "No SLA or due date is set.",
                    reason="no_deadline",
                    url=f"/tasks/{t.task_id}",
                    **base,
                )
            )
            continue
        # Blocking pauses an SLA clock, never a plain due date.
        if t.state == "breached" or (
            t.state == "paused"
            and (
                (t.deadline_from != "sla" and t.deadline < facts.now)
                or (
                    t.deadline_from == "sla"
                    and t.paused_at is not None
                    and t.paused_at >= t.deadline
                )
            )
        ):
            out.append(
                _result(
                    TASKS_SLA,
                    "task",
                    t.task_id,
                    name,
                    "fail",
                    f"Past its deadline of {_fmt(t.deadline)}.",
                    reason=(
                        "breached"
                        if t.state == "breached"
                        else "breached_before_block"
                        if t.deadline_from == "sla"
                        else "past_due_date"
                    ),
                    url=f"/tasks/{t.task_id}",
                    **base,
                )
            )
            continue
        out.append(
            _result(
                TASKS_SLA,
                "task",
                t.task_id,
                name,
                "pass",
                "Blocked, with time left on its deadline."
                if t.state == "paused"
                else f"Due {_fmt(t.deadline)}.",
                url=f"/tasks/{t.task_id}",
                **base,
            )
        )
    return out


def _controls(facts: Facts) -> list[Result]:
    """Every live control relevant to a framework the workspace runs (AU-12)."""
    out: list[Result] = []
    active = set(facts.active_frameworks)
    for c in facts.controls:
        if c.frameworks and not active & set(c.frameworks):
            continue
        name = f"{c.code} {c.name}"
        url = f"/controls/{c.id}"
        if c.status == "not_applicable":
            for check in (CONTROLS_OWNED, EVIDENCE_CURRENT):
                out.append(
                    _result(
                        check,
                        "control",
                        c.id,
                        name,
                        "not_applicable",
                        "Marked not applicable.",
                        reason="control_not_applicable",
                        url=url,
                    )
                )
            continue
        gap = _owner_gap(facts, c.owner_membership_id)
        out.append(
            _result(
                CONTROLS_OWNED,
                "control",
                c.id,
                name,
                "fail" if gap else "pass",
                gap[1] if gap else f"Owned by {_owner_name(facts, c.owner_membership_id)}.",
                reason=gap[0] if gap else None,
                url=url,
                status=c.status,
            )
        )
        if c.status != "implemented":
            out.append(
                _result(
                    EVIDENCE_CURRENT,
                    "control",
                    c.id,
                    name,
                    "not_applicable",
                    "Not implemented yet, so no operating evidence is expected.",
                    reason="not_implemented",
                    url=url,
                    status=c.status,
                )
            )
        elif c.id in facts.with_current_evidence:
            out.append(
                _result(
                    EVIDENCE_CURRENT,
                    "control",
                    c.id,
                    name,
                    "pass",
                    "Backed by evidence that still counts.",
                    url=url,
                )
            )
        else:
            expired = c.id in facts.with_any_evidence
            out.append(
                _result(
                    EVIDENCE_CURRENT,
                    "control",
                    c.id,
                    name,
                    "fail",
                    "Marked implemented, but its evidence has expired or was rejected."
                    if expired
                    else "Marked implemented with no evidence.",
                    reason="expired_or_rejected" if expired else "no_evidence",
                    url=url,
                )
            )
    return out


def _statement_of_applicability(facts: Facts) -> list[Result]:
    if facts.soa is None:
        return []
    framework_id, _framework_name, rows = facts.soa
    cutoff = _months_before(facts.today, WINDOW_MONTHS)
    out: list[Result] = []
    for row in rows:
        if row.locked:
            continue
        name = f"{row.code} {row.name}"
        base: dict[str, Any] = {
            "applicable": row.applicable,
            "justification": row.justification,
            "provided_by": row.provided_by,
            "reviewed_at": row.reviewed_at,
            "owner": _owner_name(facts, row.owner_membership_id),
        }
        if not row.applicable and not (row.justification or "").strip():
            verdict: tuple[str, str, str | None]
            verdict = ("fail", "Excluded without a reason.", "exclusion_without_reason")
        elif row.reviewed_at is None:
            verdict = ("fail", "No decision has been reviewed yet.", "not_reviewed")
        elif row.reviewed_at.astimezone(UTC).date() < cutoff:
            verdict = (
                "fail",
                f"Last reviewed {_fmt(row.reviewed_at)}, more than 12 months ago.",
                "review_lapsed",
            )
        elif row.applicable and not (row.justification or "").strip():
            verdict = (
                "fail",
                "Applies, but the reason it was included is not recorded.",
                "no_inclusion_reason",
            )
        else:
            verdict = (
                "pass",
                ("Applies" if row.applicable else "Excluded")
                + f"; reviewed {_fmt(row.reviewed_at)}.",
                None,
            )
        out.append(
            _result(
                SOA_COMPLETE,
                "requirement",
                row.requirement_id,
                name,
                verdict[0],
                verdict[1],
                reason=verdict[2],
                url=f"/frameworks/soa?framework={ISO}",
                framework_id=framework_id,
                **base,
            )
        )
    return out


def _iso_scope(facts: Facts) -> list[Result]:
    scope = facts.iso_scope
    if not scope.added or scope.framework_id is None:
        return []
    if scope.engagement_id is None:
        verdict: tuple[str, str, str | None]
        verdict = ("fail", "No ISO 27001 audit or scope has been set up.", "no_engagement")
    elif not (scope.scope_statement or "").strip():
        verdict = ("fail", "The management system scope is not written down.", "no_scope_statement")
    else:
        verdict = ("pass", "The management system scope is recorded.", None)
    return [
        _result(
            ISMS_SCOPE_RECORDED,
            "framework",
            scope.framework_id,
            scope.framework_name,
            verdict[0],
            verdict[1],
            reason=verdict[2],
            url=f"/frameworks/scope?framework={ISO}",
            engagement=scope.engagement_name,
            scope_statement_length=len((scope.scope_statement or "").strip()),
        )
    ]


def _evidence_in_window(facts: Facts) -> list[Result]:
    """The internal audit and the management review happened in the last 12 months, shown
    by evidence a person filed on the control and nobody rejected."""
    out: list[Result] = []
    today = facts.today
    cutoff = _months_before(today, WINDOW_MONTHS)
    for check in EVIDENCE_IN_WINDOW:
        for control in facts.check_controls.get(check, ()):
            name = f"{control.code} {control.name}"
            url = f"/controls/{control.id}"
            if control.status == "not_applicable":
                out.append(
                    _result(
                        check,
                        "control",
                        control.id,
                        name,
                        "not_applicable",
                        "Marked not applicable.",
                        reason="control_not_applicable",
                        url=url,
                    )
                )
                continue
            items = [
                e
                for e in facts.person_evidence.get(control.id, ())
                # The program or procedure document is not the audit or the review.
                if e.review_status != "rejected"
                and e.collected_at <= today
                and e.evidence_type != "policy_document"
            ]
            hits = [e for e in items if e.collected_at >= cutoff]
            if hits:
                newest = hits[0]
                out.append(
                    _result(
                        check,
                        "control",
                        control.id,
                        name,
                        "pass",
                        f"Evidence dated {_fmt(newest.collected_at)}: {newest.title}.",
                        url=url,
                        evidence_id=newest.id,
                        collected_at=newest.collected_at,
                        review_status=newest.review_status,
                    )
                )
            else:
                latest = items[0].collected_at if items else None
                out.append(
                    _result(
                        check,
                        "control",
                        control.id,
                        name,
                        "fail",
                        f"The latest evidence is dated {_fmt(latest)}, more than 12 months ago."
                        if latest
                        else "No evidence of it has been filed.",
                        reason="none_in_12_months" if latest else "no_evidence",
                        url=url,
                        latest_collected_at=latest,
                    )
                )
    return out


def unreachable(tenant_id: uuid.UUID, reason: str) -> list[Result]:
    """One ``error`` per check when the run itself could not read the workspace (rule 7)."""
    return [
        _result(key, "workspace", tenant_id, "This workspace", "error", reason, reason="run_failed")
        for key in IMPLEMENTED
    ]


# -- evidence -----------------------------------------------------------------------

#: The part of the snapshot each check read.
_SECTIONS: Final[dict[str, tuple[str, ...]]] = {
    ASSETS_OWNER: ("assets",),
    ASSETS_CLASSIFIED: ("assets",),
    ASSETS_REVIEWED: ("assets",),
    ASSETS_DISPOSAL: ("assets",),
    VULNS_SLA: ("findings",),
    VULNS_KEV_OWNED: ("findings",),
    RISKS_REVIEWED: ("risk_registers",),
    RISKS_TREATED: ("risk_registers",),
    RISKS_CONTROLS: ("risk_registers",),
    RISKS_ACCEPTANCE: ("risk_registers",),
    RISKS_ASSESSED: ("risk_registers",),
    VENDORS_OWNER_TIER: ("vendors",),
    VENDORS_CADENCE: ("vendors", "vendor_cadence_days"),
    VENDORS_DPA: ("vendors",),
    POLICIES_REVIEWED: ("documents",),
    POLICIES_ACKNOWLEDGED: ("documents", "acknowledgements"),
    DOCUMENTS_CONTROLLED: ("documents",),
    TASKS_SLA: ("remediation_tasks",),
    CONTROLS_OWNED: ("controls", "active_frameworks"),
    EVIDENCE_CURRENT: ("controls", "active_frameworks"),
    SOA_COMPLETE: ("statement_of_applicability",),
    ISMS_SCOPE_RECORDED: ("iso_scope",),
    INTERNAL_AUDIT: ("control_evidence",),
    MANAGEMENT_REVIEW: ("control_evidence",),
    **dict.fromkeys(DOCUMENT_TEMPLATES, ("documents",)),
}

#: What each register looked at, for the evidence file's scope block: an auditor reading a
#: clean result needs the population it was clean over (ME-5).
POPULATIONS: Final[dict[str, str]] = {
    "assets": "Assets in service (active or in maintenance); disposal looks at decommissioned "
    "and retired assets.",
    "findings": "Open critical and high findings and any with a risk acceptance; known exploited "
    "findings of any severity for ownership.",
    "risk_registers": "Open risks in active registers. Archived registers and closed risks are "
    "left out.",
    "vendors": "Vendors not terminated or archived; reassessment looks at critical and high "
    "engagements in use.",
    "documents": "Documents not archived. Required means started from a shipped template or "
    "linked to a live control.",
    "remediation_tasks": "Active top-level tasks linked to a control, vulnerability or risk; "
    "recurring occurrences and sub-tasks are left out.",
    "controls": "Live controls relevant to a framework the workspace runs.",
    "statement_of_applicability": "Every Annex A requirement of ISO 27001; clauses are always in "
    "scope and are not decided.",
    "iso_scope": "The ISO 27001 engagement of this workspace.",
    "control_evidence": "Evidence filed by people on the internal audit and management review "
    "controls; reports Verity files itself are left out.",
}


def snapshot(facts: Facts) -> dict[str, Any]:
    """The facts as the JSON an evidence file carries. People appear by membership id."""
    soa = None
    if facts.soa is not None:
        soa = {
            "framework_id": facts.soa[0],
            "framework": facts.soa[1],
            "requirements": [asdict(row) for row in facts.soa[2] if not row.locked],
        }
    data: dict[str, Any] = {
        "provider": PROVIDER,
        "evaluator": EVALUATOR,
        "collected_at": facts.now,
        "active_frameworks": list(facts.active_frameworks),
        "controls": [asdict(c) for c in facts.controls],
        "assets": [asdict(a) for a in facts.assets],
        "findings": [asdict(f) for f in facts.findings],
        "vendors": [asdict(v) for v in facts.vendors],
        "vendor_cadence_days": facts.vendor_cadence_days,
        "risk_registers": [asdict(r) for r in facts.registers],
        "documents": [asdict(d) for d in facts.documents],
        "acknowledgements": {
            str(k): {
                "campaigns": v.campaigns,
                "campaigns_current": v.campaigns_current,
                "asked": sorted(map(str, v.asked)),
                "asked_current": sorted(map(str, v.asked_current)),
                "signed_current": sorted(map(str, v.signed_current)),
                "signed_direct": sorted(map(str, v.signed_direct)),
                "late": sorted(map(str, v.late)),
            }
            for k, v in facts.acknowledgements.items()
        },
        "remediation_tasks": [asdict(t) for t in facts.remediation],
        "statement_of_applicability": soa,
        "iso_scope": asdict(facts.iso_scope),
        "control_evidence": {
            str(control_id): [asdict(e) for e in items]
            for control_id, items in facts.person_evidence.items()
        },
    }
    # Round trip through JSON so the snapshot holds only plain values.
    plain: dict[str, Any] = json.loads(json.dumps(_plain(data), default=str))
    return plain


#: Record lists whose rows carry the id a result names, so a check's file can keep only
#: the records it judged.
_RECORD_IDS: Final[dict[str, str]] = {"assets": "id", "findings": "instance_id"}


def evidence_snapshot(
    check_key: str, data: Mapping[str, Any], *, resource_ids: Iterable[str] | None = None
) -> dict[str, Any]:
    """The part of a snapshot one check read, for that check's evidence file.

    With ``resource_ids`` (the records the check gave a result for), record lists are cut
    down to those records, so the file grows with what the check judged, not with the
    whole register.
    """
    kept: dict[str, Any] = {
        key: data[key] for key in ("provider", "evaluator", "collected_at") if key in data
    }
    ids = None if resource_ids is None else set(map(str, resource_ids))
    sections = _SECTIONS.get(check_key, tuple(k for k in data if k not in kept))
    for section in sections:
        if section not in data:
            continue
        key = _RECORD_IDS.get(section)
        if ids is not None and key is not None:
            kept[section] = [row for row in data[section] if str(row.get(key)) in ids]
        else:
            kept[section] = data[section]
    kept["population"] = {s: POPULATIONS[s] for s in sections if s in POPULATIONS}
    return kept


def _plain(value: object) -> object:
    """Dates, ids and dataclasses as JSON values; everything else unchanged."""
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value
