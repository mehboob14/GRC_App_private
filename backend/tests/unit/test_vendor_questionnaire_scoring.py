"""Tiering from a tenant's own questions, and residual credit from typed answers.

The questionnaire engine replaces five fixed factors with whatever a tenant builds,
so the first test pins the promise that makes the switch safe: the shipped
"Standard" set, answered the same way, lands on the same score and tier as the
fixed arithmetic did (V6).
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from verity.modules.vendors import scoring
from verity.modules.vendors.scoring import ChoiceOption, QuestionRule

_TIERING_PACK = (
    Path(__file__).resolve().parents[2]
    / "src/verity/seed/content/vendor_tiering/questionnaire_bank.json"
)

# The library's five "lite" questions, in V6's factor order.
_FACTOR_CODES = {
    "data_sensitivity": "tier.data.sensitivity",
    "business_criticality": "tier.business.criticality",
    "system_access": "tier.system.access",
    "regulatory_scope": "tier.regulatory.scope",
    "fourth_party_reliance": "tier.fourth.party",
}


def _standard_rules() -> list[QuestionRule]:
    payload = json.loads(_TIERING_PACK.read_text(encoding="utf-8"))
    return [
        QuestionRule(
            id=q["code"],
            prompt=q["body"],
            section=q["section"],
            answer_type=q["answer_type"],
            options=tuple(
                ChoiceOption(key=o["key"], label=o["label"], score=o["score"]) for o in q["options"]
            ),
            weight=q["weight"],
        )
        for q in payload["questions"]
        if q["scope_level"] == "lite"
    ]


def _single(key: str, *options: tuple[str, float], **extra: object) -> QuestionRule:
    return QuestionRule(
        id=key,
        prompt=key,
        section="General",
        answer_type="single_choice",
        options=tuple(ChoiceOption(key=k, label=k, score=s) for k, s in options),
        **extra,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    "levels", [(0, 0, 0, 0, 0), (4, 4, 4, 4, 4), (3, 2, 1, 0, 4), (2, 2, 2, 2, 2), (4, 0, 3, 1, 2)]
)
def test_the_standard_library_set_tiers_exactly_like_the_five_factors(
    levels: tuple[int, ...],
) -> None:
    rules = _standard_rules()
    assert [r.id for r in rules] == list(_FACTOR_CODES.values())
    answers = {
        code: f"level_{level}" for code, level in zip(_FACTOR_CODES.values(), levels, strict=True)
    }
    fixed = scoring.compute_tier(dict(zip(_FACTOR_CODES, levels, strict=True)))
    built = scoring.compute_questionnaire_tier(rules, answers)
    assert built.score == fixed.score
    assert built.tier == fixed.tier


def test_every_combination_of_the_standard_set_matches_the_fixed_arithmetic() -> None:
    """Exhaustive over a coarse grid, so no weight or scale step can drift."""
    rules = _standard_rules()
    for levels in itertools.product((0, 2, 4), repeat=5):
        answers = {c: f"level_{v}" for c, v in zip(_FACTOR_CODES.values(), levels, strict=True)}
        fixed = scoring.compute_tier(dict(zip(_FACTOR_CODES, levels, strict=True)))
        built = scoring.compute_questionnaire_tier(rules, answers)
        assert (built.score, built.tier) == (fixed.score, fixed.tier), levels


def test_a_multiple_choice_counts_its_riskiest_pick() -> None:
    rule = QuestionRule(
        id="data",
        prompt="Data",
        section="Data",
        answer_type="multi_choice",
        options=(
            ChoiceOption("none", "None", 0),
            ChoiceOption("employee", "Employee", 2),
            ChoiceOption("health", "Health", 4),
        ),
    )
    result = scoring.compute_questionnaire_tier([rule], {"data": ["employee", "health"]})
    assert result.questions[0].points == 4
    assert result.score == 100.0


def test_an_option_floor_raises_the_tier_and_names_the_question() -> None:
    rules = [
        QuestionRule(
            id="data",
            prompt="Data",
            section="Data",
            answer_type="multi_choice",
            options=(
                ChoiceOption("none", "None", 0),
                ChoiceOption("health", "Health", 1, min_tier="high"),
            ),
        ),
        _single("spend", ("small", 0), ("large", 10)),
    ]
    result = scoring.compute_questionnaire_tier(rules, {"data": ["health"], "spend": "small"})
    assert result.score < 50
    assert result.band_tier != "high"
    assert result.tier == "high"
    assert result.floor_tier == "high"
    assert result.floored_by == ("data",)
    assert result.points_to_lower_tier is None


def test_a_floor_below_the_band_changes_nothing() -> None:
    rules = [
        _single("a", ("low", 0), ("high", 4)),
        QuestionRule(
            id="b",
            prompt="b",
            section="General",
            answer_type="single_choice",
            options=(ChoiceOption("x", "x", 4, min_tier="medium"),),
        ),
    ]
    result = scoring.compute_questionnaire_tier(rules, {"a": "high", "b": "x"})
    assert result.tier == "critical"
    assert result.floor_tier is None
    assert result.floored_by == ()


def test_a_hidden_question_neither_scores_nor_floors() -> None:
    rules = [
        _single("uses_ai", ("no", 0), ("yes", 1)),
        QuestionRule(
            id="trains",
            prompt="Trains on our data?",
            section="AI",
            answer_type="single_choice",
            options=(
                ChoiceOption("yes", "Yes", 4, min_tier="critical"),
                ChoiceOption("no", "No", 0),
            ),
            condition_question="uses_ai",
            condition_options=("yes",),
        ),
    ]
    # An answer left behind on a branch the assessor turned away from.
    result = scoring.compute_questionnaire_tier(rules, {"uses_ai": "no", "trains": "yes"})
    assert result.tier == "low"
    assert result.questions[1].counted is False
    assert scoring.visible_ids(rules, {"uses_ai": "yes"}) == {"uses_ai", "trains"}


def test_a_child_of_a_hidden_parent_is_hidden_too() -> None:
    rules = [
        _single("a", ("no", 0), ("yes", 1)),
        QuestionRule(
            id="b",
            prompt="b",
            section="General",
            answer_type="single_choice",
            options=(ChoiceOption("yes", "yes", 1),),
            condition_question="a",
            condition_options=("yes",),
        ),
        QuestionRule(
            id="c",
            prompt="c",
            section="General",
            answer_type="single_choice",
            options=(ChoiceOption("yes", "yes", 1),),
            condition_question="b",
            condition_options=("yes",),
        ),
    ]
    assert scoring.visible_ids(rules, {"a": "no", "b": "yes"}) == {"a"}


def test_not_applicable_and_unanswered_leave_both_sides_of_the_score() -> None:
    rules = [
        _single("a", ("low", 0), ("high", 4)),
        QuestionRule(
            id="b",
            prompt="b",
            section="General",
            answer_type="single_choice",
            options=(
                ChoiceOption("na", "Not applicable", 0, not_applicable=True),
                ChoiceOption("x", "x", 4),
            ),
        ),
        _single("c", ("low", 0), ("high", 4), required=False),
    ]
    result = scoring.compute_questionnaire_tier(rules, {"a": "high", "b": "na"})
    assert result.score == 100.0
    assert [q.counted for q in result.questions] == [True, False, False]


def test_a_questionnaire_with_nothing_scorable_lands_low_rather_than_dividing_by_zero() -> None:
    rule = QuestionRule(id="notes", prompt="Notes", section="Context", answer_type="paragraph")
    result = scoring.compute_questionnaire_tier([rule], {"notes": "Anything"})
    assert (result.score, result.tier) == (0.0, "low")


def test_residual_credit_from_a_typed_option_is_used_as_given() -> None:
    result = scoring.compute_residual(
        [
            scoring.Answer("a", "access_control", "strong", credit=1.0),
            scoring.Answer("b", "access_control", "some", credit=0.6),
        ],
        inherent=100.0,
        domain_weights={"access_control": 1.0},
    )
    posture = result.domains[0].posture
    assert posture == 0.8


def test_a_flagged_pick_on_a_critical_question_floors_the_residual() -> None:
    result = scoring.compute_residual(
        [
            scoring.Answer(
                "mfa", "access_control", "none", credit=0.0, flagged=True, critical_control=True
            )
        ],
        inherent=10.0,
    )
    assert result.critical_control_failed is True
    assert result.score == 50.0


def test_a_typed_not_applicable_is_excluded_like_na() -> None:
    result = scoring.compute_residual(
        [
            scoring.Answer("a", "access_control", "yes_key", credit=1.0),
            scoring.Answer("b", "access_control", "skip", credit=0.0, not_applicable=True),
        ],
        inherent=100.0,
    )
    domain = result.domains[0]
    assert (domain.answered, domain.not_applicable, domain.posture) == (1, 1, 1.0)
