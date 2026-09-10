"""The tiering arithmetic and the lifecycle rules — both pure, so no database.

These cover the two things V6 and V9 fix in place. If either changes, a customer's
tier changes with it, and a tier is what decides how much review work a vendor is
worth — so the numbers are asserted literally rather than recomputed by the test.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from verity.modules.vendors import lifecycle, scoring

VENDOR_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _answers(**overrides: int) -> dict[str, int]:
    return dict.fromkeys(scoring.FACTOR_KEYS, 0) | overrides


# -- scoring ------------------------------------------------------------------


def test_the_weights_normalise_to_one() -> None:
    """V6's own words. A set that does not sum to 1 cannot produce a 0..100 score."""
    assert sum(scoring.DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(scoring.DEFAULT_WEIGHTS) == set(scoring.FACTOR_KEYS)


def test_all_factors_at_the_top_of_the_scale_score_one_hundred_and_critical() -> None:
    result = scoring.compute_tier(_answers(**dict.fromkeys(scoring.FACTOR_KEYS, 4)))
    assert result.score == 100.0
    assert result.tier == "critical"
    assert result.points_to_higher_tier is None


def test_an_unanswered_assessment_scores_zero_and_lands_low() -> None:
    """A half-filled form earns the low number it has earned, rather than erroring.

    The gap then shows up as a low tier a reviewer questions, not as a failure
    that hides the record entirely.
    """
    result = scoring.compute_tier(_answers())
    assert result.score == 0.0
    assert result.tier == "low"
    assert result.points_to_lower_tier is None


@pytest.mark.parametrize(
    ("score_answers", "expected_tier", "expected_score"),
    [
        # data_sensitivity alone at 4 is 30 points -> medium (>= 25).
        ({"data_sensitivity": 4}, "medium", 30.0),
        # + business_criticality at 4 is 55 -> high (>= 50).
        ({"data_sensitivity": 4, "business_criticality": 4}, "high", 55.0),
        # + system_access at 4 is 75 -> critical, exactly on the boundary.
        (
            {"data_sensitivity": 4, "business_criticality": 4, "system_access": 4},
            "critical",
            75.0,
        ),
        # fourth_party_reliance alone at 4 is 10 -> low (< 25).
        ({"fourth_party_reliance": 4}, "low", 10.0),
    ],
)
def test_the_bands_cut_where_v6_says(
    score_answers: dict[str, int], expected_tier: str, expected_score: float
) -> None:
    result = scoring.compute_tier(_answers(**score_answers))
    assert result.score == expected_score
    assert result.tier == expected_tier


def test_a_threshold_is_inclusive_at_its_lower_bound() -> None:
    """75.0 is critical, not high. An off-by-one here silently retiers a portfolio."""
    on_boundary = scoring.compute_tier(
        _answers(data_sensitivity=4, business_criticality=4, system_access=4)
    )
    assert on_boundary.score == 75.0
    assert on_boundary.tier == "critical"


def test_an_answer_beyond_the_scale_is_clamped_and_says_so() -> None:
    """A bad import produces a defensible number, not a failed import — and the
    row still shows what was actually entered."""
    result = scoring.compute_tier(_answers(data_sensitivity=9, business_criticality=-3))
    sensitivity = next(f for f in result.factors if f.key == "data_sensitivity")
    criticality = next(f for f in result.factors if f.key == "business_criticality")
    assert (sensitivity.answer, sensitivity.clamped) == (9, 4)
    assert (criticality.answer, criticality.clamped) == (-3, 0)
    assert result.score == 30.0


def test_the_points_sum_to_the_score() -> None:
    """A breakdown whose bars do not add up to the total is worse than no breakdown."""
    result = scoring.compute_tier(
        _answers(data_sensitivity=3, business_criticality=2, system_access=4, regulatory_scope=1)
    )
    assert sum(f.points for f in result.factors) == pytest.approx(result.score, abs=0.02)


def test_the_distance_to_each_neighbouring_band_is_reported() -> None:
    """Spec ¶82's second scenario: "what would change this" without re-running the form."""
    result = scoring.compute_tier(_answers(data_sensitivity=4, business_criticality=4))
    assert result.score == 55.0
    assert result.tier == "high"
    assert result.points_to_higher_tier == 20.0  # 75 - 55
    assert result.points_to_lower_tier == 5.0  # 55 - 50


def test_a_partial_threshold_override_retunes_one_band_and_keeps_the_rest() -> None:
    """Tenant-editable JSON can arrive half-filled. A compliance calculation must
    band it, not raise from the middle of itself."""
    result = scoring.compute_tier(_answers(data_sensitivity=4), thresholds={"medium": 40.0})
    assert result.score == 30.0
    assert result.tier == "low"  # 30 is now below the retuned medium band
    assert result.thresholds["critical"] == 75.0  # the untouched bands stand


def test_a_retuned_policy_changes_the_tier() -> None:
    """The point of storing weights per tenant: the same answers, a different model."""
    answers = _answers(fourth_party_reliance=4)
    assert scoring.compute_tier(answers).tier == "low"
    reweighted = scoring.compute_tier(answers, weights={"fourth_party_reliance": 1.0})
    assert reweighted.score == 100.0
    assert reweighted.tier == "critical"


# -- the lifecycle ------------------------------------------------------------


def test_there_are_twelve_stages_in_spec_order() -> None:
    assert len(lifecycle.STAGES) == 12
    assert lifecycle.STAGES[0] == "intake"
    assert lifecycle.STAGES[-1] == "offboarding"
    assert set(lifecycle.STAGE_LABELS) == set(lifecycle.STAGES)


def test_approval_is_the_only_gate_and_tiering_is_required_instead() -> None:
    """V2 in one assertion. Tiering is unskippable without being a sign-off."""
    assert frozenset({"approval"}) == lifecycle.GATES
    assert "tiering" in lifecycle.REQUIRED_STAGES
    assert "tiering" not in lifecycle.GATES


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        ("critical", set()),
        ("high", set()),
        ("medium", {"diligence"}),
        ("low", {"diligence", "questionnaire", "scoring", "findings"}),
        (None, set()),
    ],
)
def test_each_tier_skips_what_v9_says(tier: str | None, expected: set[str]) -> None:
    assert lifecycle.skips_for(tier) == expected


def test_a_tenant_cannot_configure_a_gate_into_a_skip_list() -> None:
    """The policy row is tenant-editable, so spec ¶82 has to hold against the data
    as configured and not merely as intended."""
    hostile = {"low": ("approval", "tiering", "intake", "diligence")}
    assert lifecycle.skips_for("low", hostile) == {"diligence"}


def test_a_low_tier_cycle_runs_seven_active_stages_and_still_gates() -> None:
    """The spec's own scenario: proportionality that is visible, not implied."""
    planned = lifecycle.plan_cycle("low")
    assert len(planned) == 12
    skipped = {p.stage for p in planned if p.status == "skipped"}
    assert skipped == {"diligence", "questionnaire", "scoring", "findings"}
    active = [p for p in planned if p.status != "skipped" and p.stage != "offboarding"]
    assert len(active) == 7
    approval = next(p for p in planned if p.stage == "approval")
    assert approval.is_gate is True
    assert approval.status == "not_started"


def test_a_skipped_row_carries_the_policy_that_skipped_it() -> None:
    """ "Policy said this was disproportionate" and "someone forgot" must never
    look the same to an auditor."""
    planned = {p.stage: p for p in lifecycle.plan_cycle("medium")}
    assert planned["diligence"].skipped_by_policy == "medium tier"
    assert planned["questionnaire"].skipped_by_policy is None


def test_advancing_walks_over_skipped_rows() -> None:
    rows = [(p.stage, p.status) for p in lifecycle.plan_cycle("low")]
    assert lifecycle.next_actionable(rows, "tiering") == "contracting"
    assert lifecycle.next_actionable(rows, "offboarding") is None


# -- exit rules ---------------------------------------------------------------


def _facts(**overrides: object) -> lifecycle.StageFacts:
    base: dict[str, object] = {"vendor_id": VENDOR_ID, "vendor_name": "Acme Cloud"}
    return lifecycle.StageFacts(**(base | overrides))  # type: ignore[arg-type]


def test_every_stage_has_a_rule() -> None:
    for stage in lifecycle.STAGES:
        assert lifecycle.evaluate_exit(stage, _facts()), stage


def test_an_unknown_stage_is_a_defect_not_a_pass() -> None:
    with pytest.raises(ValueError, match="unknown stage"):
        lifecycle.evaluate_exit("nope", _facts())


def test_intake_blocks_until_owner_and_classification_are_set() -> None:
    checks = lifecycle.evaluate_exit("intake", _facts())
    codes = {c.code for c in lifecycle.blockers(checks)}
    assert codes == {"intake.owned", "intake.classified"}

    complete = lifecycle.evaluate_exit(
        "intake",
        _facts(business_owner_membership_id=uuid.uuid4(), data_classification="confidential"),
    )
    assert not lifecycle.blockers(complete)


def test_tiering_exits_only_once_an_assessment_exists() -> None:
    assert lifecycle.blockers(lifecycle.evaluate_exit("tiering", _facts()))
    scored = lifecycle.evaluate_exit("tiering", _facts(tiering_assessment_id=uuid.uuid4()))
    assert not lifecycle.blockers(scored)


def test_a_check_whose_module_is_unbuilt_is_pending_and_never_blocks() -> None:
    """The distinction rule 7 draws between error and fail, applied to a checklist.

    "We checked and it is fine" and "we cannot check yet" must not render alike.
    """
    checks = lifecycle.evaluate_exit("questionnaire", _facts())
    assert not lifecycle.blockers(checks)
    assert {c.code for c in lifecycle.pending(checks)} == {
        "questionnaire.answered",
        "questionnaire.evidenced",
    }

    built = lifecycle.evaluate_exit(
        "questionnaire", _facts(assessments_available=True, unanswered_question_count=3)
    )
    assert {c.code for c in lifecycle.blockers(built)} == {"questionnaire.answered"}


def test_contracting_only_demands_paperwork_from_the_exposed_tiers() -> None:
    for tier in ("low", "medium"):
        checks = lifecycle.evaluate_exit("contracting", _facts(tier=tier))
        assert not lifecycle.blockers(checks)
        assert not lifecycle.pending(checks)

    critical = lifecycle.evaluate_exit(
        "contracting", _facts(tier="critical", contracts_available=True, contract_count=0)
    )
    assert {c.code for c in lifecycle.blockers(critical)} == {"contracting.contract_linked"}


def test_the_gate_freshness_rule_invalidates_a_decision_that_predates_the_attempt() -> None:
    """A send-back restarts the stage, so an approval decided before that restart
    stops counting — without the append-only approval row ever being touched."""
    entered = datetime(2026, 3, 1, tzinfo=UTC)
    stale = lifecycle.evaluate_exit(
        "approval",
        _facts(
            approvals_available=True,
            stage_entered_at=entered,
            approval_decided_at=entered - timedelta(days=1),
        ),
    )
    assert {c.code for c in lifecycle.blockers(stale)} == {"approval.decided"}

    fresh = lifecycle.evaluate_exit(
        "approval",
        _facts(
            approvals_available=True,
            stage_entered_at=entered,
            approval_decided_at=entered + timedelta(minutes=1),
        ),
    )
    assert not lifecycle.blockers(fresh)


def test_diligence_names_the_reviewer_roles_that_are_still_missing() -> None:
    """A blocker that says what to do beats one that says how many there are."""
    checks = lifecycle.evaluate_exit(
        "diligence",
        _facts(
            tier="critical",
            required_reviewer_roles=("security", "legal"),
            assigned_reviewer_roles=("security",),
        ),
    )
    blocked = next(
        c for c in lifecycle.blockers(checks) if c.code == "diligence.reviewers_assigned"
    )
    assert blocked.detail is not None
    assert "legal" in blocked.detail


def test_monitoring_never_reads_as_blocked() -> None:
    """It is the resting state. Counting it as stuck would make every healthy
    vendor look like it needs attention."""
    checks = lifecycle.evaluate_exit("monitoring", _facts())
    assert not lifecycle.blockers(checks)
    assert not lifecycle.pending(checks)


# -- the machine --------------------------------------------------------------


def _state(stage: str, status: str = "in_progress") -> lifecycle.StageState:
    return lifecycle.StageState(
        stage=stage,
        status=status,
        is_gate=stage in lifecycle.GATES,
        is_required=stage in lifecycle.REQUIRED_STAGES,
    )


def test_advance_is_offered_only_when_nothing_blocks() -> None:
    blocked = lifecycle.evaluate_exit("intake", _facts())
    assert "advance" not in lifecycle.allowed_transitions(_state("intake"), blocked)

    clear = lifecycle.evaluate_exit(
        "intake", _facts(business_owner_membership_id=uuid.uuid4(), data_classification="internal")
    )
    assert "advance" in lifecycle.allowed_transitions(_state("intake"), clear)


def test_skip_is_never_offered_on_a_gate_or_a_required_stage() -> None:
    checks = lifecycle.evaluate_exit("approval", _facts(approvals_available=True))
    everything = frozenset(lifecycle.STAGES)
    assert "skip" not in lifecycle.allowed_transitions(
        _state("approval"), checks, skippable=everything
    )
    assert "skip" not in lifecycle.allowed_transitions(
        _state("tiering"), lifecycle.evaluate_exit("tiering", _facts()), skippable=everything
    )


def test_skip_is_offered_where_the_tier_permits_it() -> None:
    checks = lifecycle.evaluate_exit("diligence", _facts(tier="low"))
    moves = lifecycle.allowed_transitions(
        _state("diligence"), checks, skippable=lifecycle.skips_for("low")
    )
    assert "skip" in moves


def test_the_first_stage_cannot_be_sent_back() -> None:
    checks = lifecycle.evaluate_exit("intake", _facts())
    assert "send_back" not in lifecycle.allowed_transitions(
        _state("intake"), checks, has_earlier_stage=False
    )


def test_the_terminal_stage_offers_no_advance() -> None:
    checks = lifecycle.evaluate_exit("offboarding", _facts())
    assert "advance" not in lifecycle.allowed_transitions(_state("offboarding"), checks)


# -- residual scoring (V7) ----------------------------------------------------


def _answer(domain: str, answer: str, **kw: object) -> scoring.Answer:
    return scoring.Answer(
        question_key=kw.pop("key", f"{domain}.{answer}"),  # type: ignore[arg-type]
        domain=domain,
        answer=answer,
        **kw,  # type: ignore[arg-type]
    )


def test_a_perfect_questionnaire_still_leaves_thirty_percent_of_inherent() -> None:
    """The control ceiling, and the reason for it: a questionnaire is a claim, not
    a proof. A vendor that answers everything yes has not been audited."""
    result = scoring.compute_residual(
        [_answer("access_control", "yes"), _answer("incident_response", "yes")],
        inherent=100.0,
    )
    assert result.score == 30.0
    assert result.grade == "B"
    assert result.critical_control_failed is False


def test_answering_nothing_well_leaves_the_inherent_score_untouched() -> None:
    result = scoring.compute_residual([_answer("access_control", "no")], inherent=60.0)
    assert result.score == 60.0
    assert result.grade == "D"


def test_partial_scores_half() -> None:
    result = scoring.compute_residual([_answer("access_control", "partial")], inherent=100.0)
    assert result.score == 65.0  # 100 * (1 - 0.7 * 0.5)


def test_na_leaves_both_sides_of_the_average_rather_than_scoring_zero() -> None:
    """A question that does not apply must not look like a control that is missing."""
    mixed = scoring.compute_residual(
        [_answer("access_control", "yes"), _answer("access_control", "na")], inherent=100.0
    )
    only_yes = scoring.compute_residual([_answer("access_control", "yes")], inherent=100.0)
    assert mixed.score == only_yes.score

    domain = mixed.domains[0]
    assert (domain.answered, domain.not_applicable) == (1, 1)


def test_a_domain_answered_entirely_na_drops_out_of_the_roll_up() -> None:
    result = scoring.compute_residual(
        [_answer("access_control", "yes"), _answer("personnel_security", "na")], inherent=80.0
    )
    dropped = next(d for d in result.domains if d.domain == "personnel_security")
    assert dropped.posture is None
    assert dropped.residual is None
    # Scored as if only access_control existed.
    assert (
        result.score
        == scoring.compute_residual([_answer("access_control", "yes")], inherent=80.0).score
    )


def test_an_unanswered_questionnaire_scores_the_inherent_risk() -> None:
    """Nothing answered is nothing proven, so the review has removed no risk."""
    result = scoring.compute_residual([], inherent=72.0)
    assert result.score == 72.0
    assert result.domains == ()


def test_domain_weights_shift_the_roll_up() -> None:
    """Access control counts more than personnel security, by design."""
    result = scoring.compute_residual(
        [_answer("access_control", "no"), _answer("personnel_security", "yes")],
        inherent=100.0,
    )
    even = scoring.compute_residual(
        [_answer("access_control", "no"), _answer("personnel_security", "yes")],
        inherent=100.0,
        domain_weights={"access_control": 1.0, "personnel_security": 1.0},
    )
    assert result.score > even.score, (
        "the weighted answer is worse, because the bad one counts more"
    )


def test_a_failed_critical_control_floors_the_score_even_from_a_low_inherent() -> None:
    """However good the rest of the answers are, and however small the exposure."""
    result = scoring.compute_residual(
        [
            _answer("access_control", "yes"),
            _answer("access_control", "no", key="ac.mfa.admin", critical_control=True),
        ],
        inherent=20.0,
    )
    assert result.critical_control_failed is True
    assert result.failed_critical_keys == ("ac.mfa.admin",)
    assert result.score == 50.0


def test_the_floor_may_exceed_inherent_and_the_steps_say_which_adjustment_did_it() -> None:
    """V7 applies the floor after the clamp, deliberately: a missing named control
    is evidence the exposure factors never saw."""
    result = scoring.compute_residual(
        [_answer("access_control", "no", key="ac.mfa.admin", critical_control=True)],
        inherent=10.0,
    )
    assert result.score == 50.0 > result.inherent
    labels = [s.label for s in result.steps]
    assert labels == [
        "Inherent risk",
        "Weighted domain residual",
        "Clamp to inherent",
        "Critical-control floor",
    ]
    assert result.steps[-1].value == 50.0
    assert "no critical control" not in (result.steps[-1].detail or "")


def test_every_step_is_reported_even_when_it_did_not_fire() -> None:
    """An adjustment nobody can see is an adjustment nobody trusts, so the steps
    that did not apply say so rather than vanishing."""
    result = scoring.compute_residual([_answer("access_control", "yes")], inherent=100.0)
    clamp = next(s for s in result.steps if s.label == "Clamp to inherent")
    floor = next(s for s in result.steps if s.label == "Critical-control floor")
    assert "Not applied" in (clamp.detail or "")
    assert "Not applied" in (floor.detail or "")
    assert result.clamped is False


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        (0.0, "A"),
        (19.99, "A"),
        (20.0, "B"),
        (39.99, "B"),
        (40.0, "C"),
        (60.0, "D"),
        (80.0, "F"),
        (100.0, "F"),
    ],
)
def test_the_grade_boundaries_land_where_v7_says(score: float, grade: str) -> None:
    assert scoring.grade_for(score) == grade


def test_residual_never_silently_exceeds_inherent_without_the_clamp_firing() -> None:
    """The clamp is what makes "controls reduce risk, never add" true, so it is
    asserted rather than assumed."""
    for inherent in (0.0, 25.0, 50.0, 100.0):
        result = scoring.compute_residual(
            [_answer("access_control", "yes"), _answer("incident_response", "partial")],
            inherent=inherent,
        )
        assert result.score <= inherent + 0.01, inherent
