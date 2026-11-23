"""The company profile question catalogue (guided onboarding PR-1, PR-4, PR-5, PR-6)."""

from __future__ import annotations

from typing import Any

import pytest

from verity.core.errors import InvalidInput
from verity.modules.tenancy.profile_questions import (
    QUESTIONS,
    SECTIONS,
    core_progress,
    merge_answers,
    missing_core,
)

FULL_CORE: dict[str, Any] = {
    "description": "Payroll software for small companies.",
    "industry": "software",
    "headcount_band": "11_50",
    "hq_country": "PK",
    "operating_countries": ["PK"],
    "customer_regions": ["EU", "SA"],
    "workforce_types": "both",
    "work_arrangement": "remote",
    "offices": "none",
    "own_server_sites": "no",
    "builds_software": "yes",
    "hosting_providers": ["aws"],
    "ai_use": "staff_tools",
    "personal_data_role": "processor",
    "sensitive_data": ["none"],
    "affects_customer_financial_reporting": "not_sure",
}


def test_every_question_names_what_reads_it_and_sits_in_a_known_section() -> None:
    sections = {key for key, _ in SECTIONS}
    for question in QUESTIONS:
        assert question.used_for.strip(), question.key
        assert question.section in sections, question.key
        values = [v for v, _ in question.options]
        assert len(values) == len(set(values)), question.key
        if question.kind in {"one", "many", "tri"}:
            assert values, f"{question.key} needs options"
    assert len({q.key for q in QUESTIONS}) == len(QUESTIONS)


def test_sixteen_core_questions_and_one_more_for_the_uae() -> None:
    assert core_progress({}) == (0, 16)
    assert core_progress({"operating_countries": ["AE"]})[1] == 17


def test_not_sure_is_an_answer_and_core_answers_complete_the_profile() -> None:
    assert missing_core(FULL_CORE) == []
    assert core_progress(FULL_CORE) == (16, 16)


def test_a_uae_office_asks_which_zone() -> None:
    answers = {**FULL_CORE, "operating_countries": ["PK", "AE"]}
    assert [q.key for q in missing_core(answers)] == ["uae_zones"]


def test_a_patch_replaces_clears_and_dedupes() -> None:
    merged = merge_answers(FULL_CORE, {"customer_regions": ["EU", "EU", "GB"], "ai_use": None})
    assert merged["customer_regions"] == ["EU", "GB"]
    assert "ai_use" not in merged
    assert merge_answers({}, {"description": "   "}) == {}


@pytest.mark.parametrize(
    ("patch", "says"),
    [
        ({"industry": "farming"}, "Industry"),
        ({"sensitive_data": ["none", "health"]}, "none and something else"),
        ({"hq_country": "XX"}, "country"),
        ({"operating_countries": ["EU"]}, "countries"),
        ({"customer_regions": ["Mars"]}, "countries or regions"),
        ({"fiscal_year_end": 13}, "month"),
        ({"own_server_sites": True}, "recognise"),
        ({"no_such_question": "x"}, "does not exist"),
        ({"description": "x" * 401}, "400 characters"),
    ],
)
def test_bad_answers_are_refused_in_plain_words(patch: dict[str, Any], says: str) -> None:
    with pytest.raises(InvalidInput) as raised:
        merge_answers({}, patch)
    assert says in raised.value.message
