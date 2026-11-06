"""Verity's built-in checks, from facts.

Evaluation is a pure function of the facts a run collects, so every rule is pinned here
without a database: what passes, what fails and why, and what is not applicable. The
content pack must offer ``verity`` as the implementation of exactly the checks the
evaluator runs.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import verity
from verity.modules.assets.service import AssetCheckFacts, DisposalFacts
from verity.modules.compliance.framework_service import DecisionFact
from verity.modules.connectors import verity as checks
from verity.modules.connectors.github import Result
from verity.modules.documents.service import AckFacts, DocumentFacts
from verity.modules.evidence.service import PersonEvidence
from verity.modules.risk.service import RegisterCheckFacts, RiskCheckFact
from verity.modules.tasks.service import RemediationSla
from verity.modules.vendors.service import DpaRecord, EngagementCheckFacts, VendorCheckFacts
from verity.modules.vulnerabilities.service import SlaFinding

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
TODAY = NOW.date()
TENANT = uuid.UUID(int=1)
ALICE = uuid.UUID(int=10)
BOB = uuid.UUID(int=11)
GONE = uuid.UUID(int=12)
INVITED = uuid.UUID(int=13)


def _id(n: int) -> uuid.UUID:
    return uuid.UUID(int=1000 + n)


def _facts(**overrides: Any) -> checks.Facts:  # noqa: ANN401 — any Facts field
    base: dict[str, Any] = {
        "tenant_id": TENANT,
        "now": NOW,
        "members": {
            ALICE: checks.Member(name="Alice", status="active"),
            BOB: checks.Member(name="Bob", status="active"),
            GONE: checks.Member(name="Gone", status="disabled"),
            INVITED: checks.Member(name="New", status="invited"),
        },
        "active_frameworks": ("SOC2",),
        "controls": (),
        "check_controls": {},
        "with_current_evidence": frozenset(),
        "with_any_evidence": frozenset(),
        "person_evidence": {},
        "assets": (),
        "findings": (),
        "vendors": (),
        "vendor_cadence_days": {"critical": 180, "high": 365, "medium": 730, "low": 1095},
        # A register with a reviewed, scored risk keeps the "no assessment" rule quiet
        # unless a test is about it.
        "registers": (_register(),),
        "documents": (_doc(),),
        "acknowledgements": {},
        "remediation": (),
        "soa": None,
        "iso_scope": checks.IsoScope(
            added=False,
            engagement_id=None,
            engagement_name=None,
            scope_statement=None,
            framework_id=None,
            framework_name="ISO 27001",
        ),
    }
    base.update(overrides)
    return checks.Facts(**base)


def _of(results: list[Result], key: str) -> list[Result]:
    return [r for r in results if r.check_key == key]


def _one(results: list[Result], key: str) -> Result:
    found = _of(results, key)
    assert len(found) == 1, [r.detail for r in found]
    return found[0]


def _asset(n: int = 1, **overrides: Any) -> AssetCheckFacts:  # noqa: ANN401
    fields: dict[str, Any] = {
        "id": _id(n),
        "name": f"asset-{n}",
        "host": None,
        "asset_type": "infrastructure",
        "status": "active",
        "tier": "high",
        "data_classification": "confidential",
        "regulated_data_type": None,
        "compliance_scope": (),
        "primary_owner_membership_id": ALICE,
        "last_reviewed_at": NOW - timedelta(days=10),
        "review_days": 90,
        "disposal": None,
        "retired_from": None,
    }
    fields.update(overrides)
    return AssetCheckFacts(**fields)


def _risk(n: int = 1, **overrides: Any) -> RiskCheckFact:  # noqa: ANN401
    fields: dict[str, Any] = {
        "risk_id": _id(100 + n),
        "code": f"RSK-{n:03d}",
        "title": "Risk",
        "status": "open",
        "treatment": "mitigate",
        "owner_membership_id": ALICE,
        "inherent_score": 12,
        "effective_score": 12,
        "effective_band": "high",
        "appetite_status": None,
        "control_count": 1,
        "attention": (),
        "next_review_on": TODAY + timedelta(days=30),
        "last_reviewed_at": NOW - timedelta(days=30),
        "last_assessed_at": NOW - timedelta(days=30),
        "acceptance_id": None,
        "acceptance_status": None,
        "acceptance_expires_on": None,
        "acceptance_approver_membership_id": None,
    }
    fields.update(overrides)
    return RiskCheckFact(**fields)


def _register(*risks: RiskCheckFact, status: str = "active") -> RegisterCheckFacts:
    return RegisterCheckFacts(
        register_id=_id(90),
        name="Enterprise",
        status=status,
        is_default=True,
        review_cadence_days=90,
        lowest_band="low",
        closed_count=0,
        risks=risks or (_risk(),),
    )


def _doc(n: int = 1, **overrides: Any) -> DocumentFacts:  # noqa: ANN401
    fields: dict[str, Any] = {
        "id": _id(200 + n),
        "code": f"POL-{n:02d}",
        "title": "Information Security Policy",
        "doc_type": "policy",
        "lifecycle": "published",
        "template_key": "information-security-policy",
        "owner_membership_id": ALICE,
        "renewal_date": TODAY + timedelta(days=200),
        "approved_at": NOW - timedelta(days=100),
        "published_at": NOW - timedelta(days=100),
        "gap": None,
        "current_version_no": "1.0",
        "current_version_created_at": NOW - timedelta(days=101),
        "current_version_author_id": BOB,
        "control_ids": (),
        "tiers": (
            (1, "approved", NOW - timedelta(days=100)),
            (2, "approved", NOW - timedelta(days=100)),
        ),
        "approver_ids": (ALICE,),
        "open_placeholders": 0,
    }
    fields.update(overrides)
    return DocumentFacts(**fields)


def _control(code: str, n: int, **overrides: Any) -> checks.ControlFact:  # noqa: ANN401
    fields: dict[str, Any] = {
        "id": _id(300 + n),
        "code": code,
        "name": code,
        "status": "implemented",
        "owner_membership_id": ALICE,
        "template_id": _id(400 + n),
        "frameworks": ("SOC2",),
    }
    fields.update(overrides)
    return checks.ControlFact(**fields)


# -- the content pack and the evaluator agree -----------------------------------------------


def test_the_pack_offers_verity_for_exactly_the_checks_the_evaluator_runs() -> None:
    path = Path(verity.__file__).parent / "seed" / "content" / "automation" / "checks.json"
    shipped = {
        c["key"]
        for c in json.loads(path.read_text(encoding="utf-8"))
        if "verity" in c["implementations"]
    }
    assert shipped == set(checks.IMPLEMENTED)


def test_every_result_names_its_rule_and_says_what_it_found() -> None:
    results = checks.evaluate(_facts(assets=(_asset(),)))
    assert results
    for result in results:
        assert result.detail["rule"] == checks.EVALUATOR
        assert result.detail["summary"]
        assert result.outcome in {"pass", "fail", "error", "not_applicable"}
        for dash in (chr(0x2014), chr(0x2013)):  # em and en dash
            assert dash not in result.detail["summary"]


# -- assets ---------------------------------------------------------------------------------


def test_an_asset_in_service_needs_an_owner_who_can_act() -> None:
    results = checks.evaluate(
        _facts(
            assets=(
                _asset(1),
                _asset(2, primary_owner_membership_id=None),
                _asset(3, primary_owner_membership_id=GONE),
                _asset(4, primary_owner_membership_id=INVITED),
                _asset(5, status="planned", primary_owner_membership_id=None),
            )
        )
    )
    owners = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.ASSETS_OWNER)
    }
    assert owners == {
        "asset-1": ("pass", None),
        "asset-2": ("fail", "no_owner"),
        "asset-3": ("fail", "owner_inactive"),
        "asset-4": ("fail", "owner_inactive"),
    }


def test_an_asset_is_classified_and_reviewed_within_its_window() -> None:
    results = checks.evaluate(
        _facts(
            assets=(
                _asset(1, data_classification=None),
                _asset(2, last_reviewed_at=None),
                _asset(3, last_reviewed_at=NOW - timedelta(days=91)),
                _asset(4, last_reviewed_at=NOW - timedelta(days=90)),
            )
        )
    )
    classified = {r.resource_name: r.outcome for r in _of(results, checks.ASSETS_CLASSIFIED)}
    assert classified["asset-1"] == "fail"
    assert classified["asset-2"] == "pass"
    reviewed = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.ASSETS_REVIEWED)
    }
    assert reviewed["asset-2"] == ("fail", "never_reviewed")
    assert reviewed["asset-3"] == ("fail", "review_overdue")
    assert reviewed["asset-4"] == ("pass", None)


def test_disposal_needs_a_record_and_sanitised_media() -> None:
    record = DisposalFacts(
        disposal_method="wiped_and_recycled",
        media_sanitised=True,
        evidence_ref=None,
        reason="End of life",
        decommissioned_by_membership_id=ALICE,
        decommissioned_at=NOW - timedelta(days=5),
    )
    results = checks.evaluate(
        _facts(
            assets=(
                _asset(1, status="decommissioned", disposal=record),
                _asset(2, status="decommissioned"),
                _asset(3, status="retired", retired_from="planned"),
                _asset(4, status="retired", disposal=replace(record, media_sanitised=False)),
                _asset(
                    5,
                    status="retired",
                    asset_type="application",
                    disposal=replace(record, media_sanitised=False),
                ),
                _asset(
                    6,
                    status="retired",
                    disposal=replace(
                        record, media_sanitised=False, disposal_method="physically_destroyed"
                    ),
                ),
            )
        )
    )
    verdict = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.ASSETS_DISPOSAL)
    }
    assert verdict == {
        "asset-1": ("pass", None),
        "asset-2": ("fail", "no_disposal_record"),
        "asset-3": ("not_applicable", "never_in_service"),
        "asset-4": ("fail", "media_not_sanitised"),
        "asset-5": ("pass", None),
        "asset-6": ("pass", None),
    }
    # An asset out of service is not judged for owner, class or review.
    assert not _of(results, checks.ASSETS_OWNER)


# -- vulnerabilities ------------------------------------------------------------------------


def _finding(n: int, **overrides: Any) -> SlaFinding:  # noqa: ANN401
    fields: dict[str, Any] = {
        "instance_id": _id(500 + n),
        "cve_id": f"CVE-2026-{n:04d}",
        "title": "Flaw",
        "severity": "critical",
        "kev_flag": False,
        "state": "active",
        "asset_id": _id(1),
        "asset_name": "web",
        "locator": "",
        "owner_membership_id": ALICE,
        "first_detected_at": NOW - timedelta(days=20),
        "sla_due_at": NOW + timedelta(days=5),
        "accepted_expires_at": None,
        "waiver_live": False,
        "effectively_open": True,
        "past_sla": False,
    }
    fields.update(overrides)
    return SlaFinding(**fields)


def test_urgent_findings_are_fixed_within_their_sla_unless_accepted() -> None:
    results = checks.evaluate(
        _facts(
            findings=(
                _finding(1),
                _finding(2, sla_due_at=NOW - timedelta(days=3), past_sla=True),
                _finding(
                    3,
                    state="accepted",
                    waiver_live=True,
                    effectively_open=False,
                    accepted_expires_at=NOW + timedelta(days=30),
                ),
                _finding(4, severity="medium", past_sla=True),
                _finding(5, sla_due_at=None),
            )
        )
    )
    verdict = {
        r.resource_id: (r.outcome, r.detail.get("reason")) for r in _of(results, checks.VULNS_SLA)
    }
    assert verdict == {
        str(_id(501)): ("pass", None),
        str(_id(502)): ("fail", "past_sla"),
        str(_id(503)): ("pass", "risk_accepted"),
        str(_id(505)): ("fail", "no_sla_date"),
    }


def test_known_exploited_findings_need_an_owner_who_can_act() -> None:
    results = checks.evaluate(
        _facts(
            findings=(
                _finding(1, kev_flag=True, severity="low"),
                _finding(2, kev_flag=True, owner_membership_id=None),
                _finding(3, kev_flag=True, owner_membership_id=INVITED),
                _finding(
                    4, kev_flag=True, state="accepted", waiver_live=True, effectively_open=False
                ),
            )
        )
    )
    verdict = {r.resource_id: r.outcome for r in _of(results, checks.VULNS_KEV_OWNED)}
    assert verdict == {str(_id(501)): "pass", str(_id(502)): "fail", str(_id(503)): "fail"}


# -- risks ----------------------------------------------------------------------------------


def test_risks_are_reviewed_owned_treated_and_linked() -> None:
    register = _register(
        _risk(1),
        _risk(2, next_review_on=TODAY - timedelta(days=1)),
        _risk(3, owner_membership_id=GONE),
        _risk(4, treatment=None),
        _risk(5, treatment="accept"),
        _risk(6, control_count=0),
        _risk(7, effective_band="low"),
        _risk(8, appetite_status="within", effective_band="critical"),
        _risk(9, inherent_score=None, effective_score=None, effective_band=None),
    )
    results = checks.evaluate(_facts(registers=(register,)))
    reviewed = {
        r.resource_name: r.detail.get("reason")
        for r in _of(results, checks.RISKS_REVIEWED)
        if r.outcome == "fail"
    }
    assert reviewed == {"RSK-002 Risk": "review_overdue"}
    treated = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.RISKS_TREATED)
    }
    assert treated["RSK-001 Risk"] == ("pass", None)
    assert treated["RSK-003 Risk"] == ("fail", "owner_inactive")
    assert treated["RSK-004 Risk"] == ("fail", "no_treatment")
    assert treated["RSK-005 Risk"] == ("fail", "acceptance_not_in_force")
    assert treated["RSK-007 Risk"] == ("not_applicable", "within_appetite")
    assert treated["RSK-008 Risk"] == ("not_applicable", "within_appetite")
    assert treated["RSK-009 Risk"] == ("fail", "unscored")
    linked = {r.resource_name: r.outcome for r in _of(results, checks.RISKS_CONTROLS)}
    assert linked["RSK-006 Risk"] == "fail"
    assert linked["RSK-001 Risk"] == "pass"
    assert "RSK-004 Risk" not in linked  # undecided treatment: not judged as mitigation


def test_an_accepted_risk_needs_an_acceptance_in_force() -> None:
    register = _register(
        _risk(
            1,
            status="accepted",
            treatment="accept",
            acceptance_status="active",
            acceptance_expires_on=TODAY + timedelta(days=1),
        ),
        _risk(
            2,
            status="accepted",
            treatment="accept",
            acceptance_status="active",
            acceptance_expires_on=TODAY - timedelta(days=1),
        ),
        _risk(3, status="accepted", treatment="accept"),
    )
    results = checks.evaluate(_facts(registers=(register,)))
    verdict = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.RISKS_ACCEPTANCE)
    }
    assert verdict == {
        "RSK-001 Risk": ("pass", None),
        "RSK-002 Risk": ("fail", "expired"),
        "RSK-003 Risk": ("fail", "no_acceptance_in_force"),
    }
    # The treatment check does not wait for the daily sweep to reopen an expired acceptance.
    treated = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.RISKS_TREATED)
    }
    assert treated["RSK-001 Risk"] == ("pass", None)
    assert treated["RSK-002 Risk"] == ("fail", "acceptance_not_in_force")


def test_a_risk_assessment_covers_every_open_risk_in_the_last_year() -> None:
    fresh = checks.evaluate(_facts(registers=(_register(_risk(1)),)))
    assert _one(fresh, checks.RISKS_ASSESSED).outcome == "pass"
    stale = checks.evaluate(
        _facts(
            registers=(_register(_risk(1), _risk(2, last_assessed_at=NOW - timedelta(days=400))),)
        )
    )
    assert _one(stale, checks.RISKS_ASSESSED).detail["reason"] == "stale_risks"
    nothing = checks.evaluate(_facts(registers=()))
    result = _one(nothing, checks.RISKS_ASSESSED)
    assert (result.outcome, result.detail["reason"]) == ("fail", "no_assessment_recorded")
    archived = checks.evaluate(_facts(registers=(_register(_risk(1), status="archived"),)))
    assert _one(archived, checks.RISKS_ASSESSED).detail["reason"] == "no_assessment_recorded"


# -- vendors --------------------------------------------------------------------------------


def _engagement(n: int, **overrides: Any) -> EngagementCheckFacts:  # noqa: ANN401
    fields: dict[str, Any] = {
        "id": _id(600 + n),
        "name": f"Engagement {n}",
        "tier": "critical",
        "status": "active",
        "last_review_completed_at": NOW - timedelta(days=30),
    }
    fields.update(overrides)
    return EngagementCheckFacts(**fields)


def _vendor(n: int, **overrides: Any) -> VendorCheckFacts:  # noqa: ANN401
    fields: dict[str, Any] = {
        "id": _id(700 + n),
        "name": f"Vendor {n}",
        "lifecycle_status": "active",
        "tier": "critical",
        "business_owner_membership_id": ALICE,
        "stores_pii": False,
        "data_types_in_scope": (),
        "data_classification": None,
        "next_reassessment_on": TODAY + timedelta(days=100),
        "engagements": (_engagement(n),),
        "dpas": (),
    }
    fields.update(overrides)
    return VendorCheckFacts(**fields)


def test_vendors_are_owned_tiered_and_reassessed_on_cadence() -> None:
    results = checks.evaluate(
        _facts(
            vendors=(
                _vendor(1),
                _vendor(2, tier=None),
                _vendor(3, next_reassessment_on=TODAY - timedelta(days=1)),
                _vendor(
                    4,
                    engagements=(
                        _engagement(4, last_review_completed_at=NOW - timedelta(days=200)),
                    ),
                ),
                _vendor(5, engagements=(_engagement(5, tier="low"),)),
                _vendor(6, lifecycle_status="archived"),
            )
        )
    )
    owner = {r.resource_name: r.outcome for r in _of(results, checks.VENDORS_OWNER_TIER)}
    assert owner == {
        "Vendor 1": "pass",
        "Vendor 2": "fail",
        "Vendor 3": "pass",
        "Vendor 4": "pass",
        "Vendor 5": "pass",
    }
    cadence = {r.resource_name: r.outcome for r in _of(results, checks.VENDORS_CADENCE)}
    assert cadence == {
        "Vendor 1": "pass",
        "Vendor 2": "pass",
        "Vendor 3": "fail",
        "Vendor 4": "fail",
        "Vendor 5": "not_applicable",
    }


def test_a_vendor_holding_personal_data_has_an_agreement_in_force() -> None:
    signed = DpaRecord(
        kind="document",
        id=_id(801),
        title="DPA",
        status="reviewed",
        valid_until=None,
        evidence_attached=True,
    )
    results = checks.evaluate(
        _facts(
            vendors=(
                _vendor(1, stores_pii=True, dpas=(signed,)),
                _vendor(2, stores_pii=True),
                _vendor(
                    3,
                    stores_pii=True,
                    dpas=(replace(signed, valid_until=TODAY - timedelta(days=1)),),
                ),
                _vendor(
                    4, stores_pii=True, dpas=(replace(signed, kind="contract", status="draft"),)
                ),
                _vendor(5),
                _vendor(7, stores_pii=True, dpas=(replace(signed, evidence_attached=False),)),
                # Still under review: the agreement is checked once it is in use.
                _vendor(
                    6,
                    stores_pii=True,
                    lifecycle_status="under_review",
                    engagements=(
                        _engagement(6, last_review_completed_at=None, status="requested"),
                    ),
                ),
                # Already in use without a completed review: judged like any vendor in use.
                _vendor(
                    8,
                    stores_pii=True,
                    engagements=(
                        _engagement(8, last_review_completed_at=None, status="requested"),
                    ),
                ),
            )
        )
    )
    verdict = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.VENDORS_DPA)
    }
    assert verdict == {
        "Vendor 1": ("pass", None),
        "Vendor 2": ("fail", "no_dpa"),
        "Vendor 3": ("fail", "dpa_expired"),
        "Vendor 4": ("fail", "dpa_not_in_force"),
        "Vendor 5": ("not_applicable", "no_personal_data"),
        "Vendor 6": ("not_applicable", "not_approved"),
        "Vendor 7": ("fail", "dpa_not_attached"),
        "Vendor 8": ("fail", "no_dpa"),
    }


# -- documents ------------------------------------------------------------------------------


def test_required_policies_are_current_and_filled_in() -> None:
    results = checks.evaluate(
        _facts(
            documents=(
                _doc(1),
                _doc(2, gap="review_overdue"),
                _doc(3, open_placeholders=4),
                _doc(4, template_key=None),  # not required: no template, no control
            )
        )
    )
    verdict = {
        r.resource_name.split()[0]: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.POLICIES_REVIEWED)
    }
    assert verdict == {
        "POL-01": ("pass", None),
        "POL-02": ("fail", "review_overdue"),
        "POL-03": ("fail", "unfilled_placeholders"),
    }
    empty = checks.evaluate(_facts(documents=()))
    assert _one(empty, checks.POLICIES_REVIEWED).detail["reason"] == "no_policies"


def _ack(doc: DocumentFacts, **overrides: Any) -> AckFacts:  # noqa: ANN401
    fields: dict[str, Any] = {
        "document_id": doc.id,
        "published_at": NOW - timedelta(days=30),
        "campaigns": 1,
        "campaigns_current": 1,
        "asked": frozenset(),
        "asked_current": frozenset(),
        "signed_current": frozenset(),
        "signed_direct": frozenset(),
        "late": frozenset(),
        "next_due_at": None,
    }
    fields.update(overrides)
    if "asked" not in overrides:
        fields["asked"] = fields["asked_current"]
    return AckFacts(**fields)


def test_acknowledgement_counts_only_signatures_of_the_current_text_by_people_who_can_act() -> None:
    conduct = _doc(1, template_key="code-of-conduct", title="Code of Conduct")
    other = _doc(2)
    third = _doc(3)
    acks = {
        other.id: _ack(
            other,
            asked_current=frozenset({ALICE, BOB, GONE}),
            signed_current=frozenset({ALICE}),
            late=frozenset({BOB, GONE}),
        ),
        third.id: _ack(third, asked_current=frozenset({ALICE}), signed_current=frozenset({ALICE})),
    }
    results = checks.evaluate(_facts(documents=(conduct, other, third), acknowledgements=acks))
    verdict = {
        r.resource_name.split()[0]: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.POLICIES_ACKNOWLEDGED)
    }
    assert verdict == {
        "POL-01": ("fail", "never_sent"),
        "POL-02": ("fail", "late"),
        "POL-03": ("pass", None),
    }
    late = next(
        r
        for r in _of(results, checks.POLICIES_ACKNOWLEDGED)
        if r.resource_name.startswith("POL-02")
    )
    assert late.detail["late"] == 1  # the removed member does not count


def test_the_code_of_conduct_binds_every_member_of_staff_not_just_a_campaign_list() -> None:
    guest = _id(99)
    members = {
        ALICE: checks.Member(name="Alice", status="active"),
        BOB: checks.Member(name="Bob", status="active"),
        guest: checks.Member(name="Auditor", status="active"),
    }
    partial = _doc(1, template_key="code-of-conduct", title="Code of Conduct")
    direct = _doc(2, template_key="acceptable-use-policy", title="Acceptable Use Policy")
    republished = _doc(3)
    acks = {
        # Sent to Alice only, and she signed: Bob was never asked, so it fails.
        partial.id: _ack(
            partial, asked_current=frozenset({ALICE}), signed_current=frozenset({ALICE})
        ),
        # No campaign, but all staff signed the current version directly; the guest is not staff.
        direct.id: _ack(
            direct, campaigns=0, campaigns_current=0, signed_direct=frozenset({ALICE, BOB})
        ),
        # Asked for an earlier version only: nothing is owed for this one yet.
        republished.id: _ack(
            republished, campaigns_current=0, asked=frozenset({ALICE}), late=frozenset()
        ),
    }
    results = checks.evaluate(
        _facts(
            members=members,
            guests=frozenset({guest}),
            documents=(partial, direct, republished),
            acknowledgements=acks,
        )
    )
    verdict = {
        r.resource_name.split()[0]: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.POLICIES_ACKNOWLEDGED)
    }
    assert verdict == {
        "POL-01": ("fail", "not_asked"),
        "POL-02": ("pass", None),
        "POL-03": ("not_applicable", "not_sent_for_current_version"),
    }
    missing = _one(
        [r for r in results if r.resource_name.startswith("POL-01")], checks.POLICIES_ACKNOWLEDGED
    )
    assert (missing.detail["missing"], missing.detail["expected"]) == (1, 2)
    assert "Bob" in missing.detail["summary"]


def test_iso_documents_pass_on_a_current_template_document_or_a_linked_one() -> None:
    scope = _control("GOV-23", 23)
    parties = _control("GOV-25", 25)
    results = checks.evaluate(
        _facts(
            check_controls={
                checks.ISMS_SCOPE_DOCUMENTED: (scope,),
                checks.PARTIES_DOCUMENTED: (parties,),
                checks.OBJECTIVES_DOCUMENTED: (_control("GOV-26", 26),),
            },
            documents=(
                _doc(1, template_key="isms-scope-statement"),
                _doc(2, template_key=None, control_ids=(parties.id,), gap="not_published"),
            ),
        )
    )
    assert _one(results, checks.ISMS_SCOPE_DOCUMENTED).outcome == "pass"
    assert _one(results, checks.PARTIES_DOCUMENTED).detail["reason"] == "not_current"
    assert _one(results, checks.OBJECTIVES_DOCUMENTED).detail["reason"] == "missing"
    # No control mapped (ISO not added): the check has nothing to judge.
    assert not _of(results, checks.COMMUNICATION_DOCUMENTED)


def test_a_published_document_is_owned_approved_for_its_current_text_and_under_review() -> None:
    results = checks.evaluate(
        _facts(
            documents=(
                _doc(1),
                _doc(2, owner_membership_id=None),
                _doc(3, current_version_created_at=NOW - timedelta(days=1)),
                _doc(4, tiers=(), approver_ids=()),
                _doc(5, renewal_date=TODAY - timedelta(days=1), gap="review_overdue"),
                _doc(6, lifecycle="draft"),
                # Approved years ago with the review date pushed out: not current.
                _doc(7, gap="approval_older_than_interval"),
            )
        )
    )
    verdict = {
        r.resource_name.split()[0]: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.DOCUMENTS_CONTROLLED)
    }
    assert verdict == {
        "POL-01": ("pass", None),
        "POL-02": ("fail", "no_owner"),
        "POL-03": ("fail", "approval_predates_current_version"),
        "POL-04": ("fail", "no_approval_record"),
        "POL-05": ("fail", "review_overdue"),
        "POL-07": ("fail", "approval_older_than_interval"),
    }


# -- tasks, controls, evidence --------------------------------------------------------------


def test_remediation_tasks_keep_to_their_deadline() -> None:
    def task(n: int, **overrides: Any) -> RemediationSla:  # noqa: ANN401
        fields: dict[str, Any] = {
            "task_id": _id(900 + n),
            "code": f"TSK-{n:04d}",
            "title": "Fix",
            "task_kind": "task",
            "status": "open",
            "sla_level": "P2",
            "deadline": NOW + timedelta(days=3),
            "deadline_from": "sla",
            "paused_at": None,
            "state": "on_track",
            "linked_to": ("risk",),
        }
        fields.update(overrides)
        return RemediationSla(**fields)

    results = checks.evaluate(
        _facts(
            remediation=(
                task(1),
                task(2, state="breached", deadline=NOW - timedelta(hours=1)),
                task(
                    3,
                    state="paused",
                    status="blocked",
                    paused_at=NOW - timedelta(hours=1),
                    deadline=NOW - timedelta(hours=2),
                ),
                task(4, state="paused", status="blocked", paused_at=NOW - timedelta(hours=3)),
                task(5, state="none", deadline=None, deadline_from=None),
                # Blocking pauses an SLA clock, never a plain due date.
                task(
                    6,
                    state="paused",
                    status="blocked",
                    sla_level=None,
                    deadline_from="due_date",
                    paused_at=NOW - timedelta(hours=3),
                    deadline=NOW - timedelta(hours=1),
                ),
                task(7, state="paused", status="blocked", deadline=None, deadline_from=None),
            )
        )
    )
    verdict = {
        r.resource_name.split()[0]: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.TASKS_SLA)
    }
    assert verdict == {
        "TSK-0001": ("pass", None),
        "TSK-0002": ("fail", "breached"),
        "TSK-0003": ("fail", "breached_before_block"),
        "TSK-0004": ("pass", None),
        "TSK-0005": ("not_applicable", "no_deadline"),
        "TSK-0006": ("fail", "past_due_date"),
        "TSK-0007": ("not_applicable", "no_deadline"),
    }


def test_controls_of_frameworks_the_workspace_runs_are_owned_and_evidenced() -> None:
    owned = _control("GOV-09", 1)
    unowned = _control("IAM-01", 2, owner_membership_id=None)
    expired = _control("IAM-02", 3)
    started = _control("IAM-03", 4, status="in_progress")
    other_framework = _control("GOV-23", 5, owner_membership_id=None, frameworks=("ISO27001",))
    results = checks.evaluate(
        _facts(
            controls=(owned, unowned, expired, started, other_framework),
            with_current_evidence=frozenset({owned.id, unowned.id}),
            with_any_evidence=frozenset({owned.id, unowned.id, expired.id}),
        )
    )
    owner = {r.resource_name: r.outcome for r in _of(results, checks.CONTROLS_OWNED)}
    assert owner == {
        "GOV-09 GOV-09": "pass",
        "IAM-01 IAM-01": "fail",
        "IAM-02 IAM-02": "pass",
        "IAM-03 IAM-03": "pass",
    }
    evidence = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.EVIDENCE_CURRENT)
    }
    assert evidence == {
        "GOV-09 GOV-09": ("pass", None),
        "IAM-01 IAM-01": ("pass", None),
        "IAM-02 IAM-02": ("fail", "expired_or_rejected"),
        "IAM-03 IAM-03": ("not_applicable", "not_implemented"),
    }


def test_the_internal_audit_and_management_review_need_a_person_filed_record_this_year() -> None:
    audit = _control("GOV-13", 13)
    review = _control("GOV-15", 15)

    def item(days_ago: int, status: str = "pending", kind: str = "other") -> PersonEvidence:
        return PersonEvidence(
            id=uuid.uuid4(),
            title="Report",
            evidence_type=kind,
            collected_at=TODAY - timedelta(days=days_ago),
            review_status=status,
        )

    results = checks.evaluate(
        _facts(
            check_controls={checks.INTERNAL_AUDIT: (audit,), checks.MANAGEMENT_REVIEW: (review,)},
            person_evidence={audit.id: (item(30),), review.id: (item(30, "rejected"), item(500))},
        )
    )
    assert _one(results, checks.INTERNAL_AUDIT).outcome == "pass"
    review_result = _one(results, checks.MANAGEMENT_REVIEW)
    assert (review_result.outcome, review_result.detail["reason"]) == ("fail", "none_in_12_months")
    # The audit program or procedure document is not the audit itself.
    program_only = checks.evaluate(
        _facts(
            check_controls={checks.INTERNAL_AUDIT: (audit,)},
            person_evidence={audit.id: (item(30, kind="policy_document"),)},
        )
    )
    assert _one(program_only, checks.INTERNAL_AUDIT).outcome == "fail"


def test_a_control_page_gets_failures_first_and_every_plan_limited_result() -> None:
    from verity.modules.connectors.models import CheckResult  # noqa: PLC0415
    from verity.modules.connectors.service import RESULTS_SHOWN, _shown  # noqa: PLC0415

    order = {"fail": 0, "error": 1, "pass": 2, "not_applicable": 3}

    def row(n: int, outcome: str, reason: str | None = None) -> CheckResult:
        return CheckResult(
            resource_name=f"r{n:04d}", outcome=outcome, detail={"reason": reason} if reason else {}
        )

    rows = [row(n, "pass") for n in range(RESULTS_SHOWN + 50)]
    rows += [row(9000 + n, "fail") for n in range(3)]
    rows += [row(9100 + n, "fail", "plan") for n in range(5)]
    shown = _shown(rows, order)
    assert len(shown) == RESULTS_SHOWN + 5
    assert [r.outcome for r in shown[:3]] == ["fail"] * 3
    assert sum(1 for r in shown if r.detail.get("reason") == "plan") == 5


# -- ISO 27001 ------------------------------------------------------------------------------


def test_the_statement_of_applicability_is_decided_reviewed_and_justified() -> None:
    def row(code: str, **overrides: Any) -> DecisionFact:  # noqa: ANN401
        fields: dict[str, Any] = {
            "requirement_id": uuid.uuid4(),
            "code": code,
            "name": code,
            "locked": False,
            "applicable": True,
            "justification": "Treats risk RSK-001.",
            "provided_by": "organization",
            "owner_membership_id": ALICE,
            "reviewed_at": NOW - timedelta(days=10),
        }
        fields.update(overrides)
        return DecisionFact(**fields)

    rows = (
        row("4.1", locked=True, reviewed_at=None),
        row("A.5.1"),
        row("A.5.2", reviewed_at=None),
        row("A.5.3", reviewed_at=NOW - timedelta(days=400)),
        row("A.5.4", justification=None),
        row("A.7.6", applicable=False, justification="No premises."),
    )
    results = checks.evaluate(_facts(soa=(uuid.uuid4(), "ISO 27001", rows)))
    verdict = {
        r.resource_name: (r.outcome, r.detail.get("reason"))
        for r in _of(results, checks.SOA_COMPLETE)
    }
    assert verdict == {
        "A.5.1 A.5.1": ("pass", None),
        "A.5.2 A.5.2": ("fail", "not_reviewed"),
        "A.5.3 A.5.3": ("fail", "review_lapsed"),
        "A.5.4 A.5.4": ("fail", "no_inclusion_reason"),
        "A.7.6 A.7.6": ("pass", None),
    }
    assert not _of(checks.evaluate(_facts()), checks.SOA_COMPLETE)


def test_the_management_system_scope_is_recorded_once_iso_is_added() -> None:
    scope = checks.IsoScope(
        added=True,
        engagement_id=uuid.uuid4(),
        engagement_name="ISO 27001 certification 2026",
        scope_statement="The Verity platform, its cloud hosting and the people who run it.",
        framework_id=uuid.uuid4(),
        framework_name="ISO 27001",
    )
    assert (
        _one(checks.evaluate(_facts(iso_scope=scope)), checks.ISMS_SCOPE_RECORDED).outcome == "pass"
    )
    blank = replace(scope, scope_statement="  ")
    assert _one(checks.evaluate(_facts(iso_scope=blank)), checks.ISMS_SCOPE_RECORDED).detail[
        "reason"
    ] == ("no_scope_statement")
    assert not _of(checks.evaluate(_facts()), checks.ISMS_SCOPE_RECORDED)


# -- evidence snapshot ----------------------------------------------------------------------


def test_the_evidence_file_holds_the_part_of_the_snapshot_a_check_read() -> None:
    facts = _facts(assets=(_asset(),))
    data = checks.snapshot(facts)
    json.dumps(data)  # plain JSON only
    kept = checks.evidence_snapshot(checks.ASSETS_OWNER, data)
    assert set(kept) == {"provider", "evaluator", "collected_at", "assets", "population"}
    assert kept["assets"][0]["name"] == "asset-1"
    assert kept["population"]["assets"].startswith("Assets in service")
    # Given the records the check judged, the file keeps only those.
    two = checks.snapshot(_facts(assets=(_asset(1), _asset(2))))
    cut = checks.evidence_snapshot(checks.ASSETS_OWNER, two, resource_ids={str(_id(2))})
    assert [a["id"] for a in cut["assets"]] == [str(_id(2))]


@pytest.mark.parametrize("key", checks.IMPLEMENTED)
def test_a_failed_run_reads_could_not_check_never_failing(key: str) -> None:
    results = [r for r in checks.unreachable(TENANT, "down") if r.check_key == key]
    assert [r.outcome for r in results] == ["error"]


def test_dates_in_the_snapshot_are_iso_strings() -> None:
    data = checks.snapshot(_facts(assets=(_asset(),)))
    assert data["assets"][0]["last_reviewed_at"].startswith("2026-")
    assert date.fromisoformat(data["collected_at"][:10]) == TODAY
