"""The risk register's pure rules, without a database."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from verity.core.errors import InvalidInput
from verity.modules.risk import scoring
from verity.modules.risk.assist import rank_templates
from verity.modules.risk.models import MAX_LEVELS, MIN_LEVELS
from verity.modules.risk.transfer import (
    ImportRow,
    _choice,
    _date,
    _int,
    _normalise_header,
    read_rows,
)

LIBRARY = Path(__file__).parents[2] / "src/verity/seed/content/risk_library/risk_templates.json"


def test_default_bands_land_on_the_familiar_five_by_five_thresholds() -> None:
    bands = scoring.default_bands(25)
    assert [b["min_score"] for b in bands] == [1, 5, 10, 15]
    assert [b["key"] for b in bands] == ["low", "medium", "high", "critical"]


@pytest.mark.parametrize("levels", [(3, 3), (3, 4), (4, 4), (5, 5), (6, 6), (3, 6)])
def test_default_bands_rise_strictly_for_every_matrix_size(levels: tuple[int, int]) -> None:
    max_score = levels[0] * levels[1]
    mins = [b["min_score"] for b in scoring.default_bands(max_score)]
    assert mins[0] == 1
    assert all(a < b for a, b in itertools.pairwise(mins))
    assert mins[-1] <= max_score


def test_band_for_picks_the_highest_band_reached() -> None:
    bands = scoring.default_bands(25)
    assert scoring.band_for(bands, None) is None
    assert scoring.band_for(bands, 1) == "low"
    assert scoring.band_for(bands, 4) == "low"
    assert scoring.band_for(bands, 5) == "medium"
    assert scoring.band_for(bands, 14) == "high"
    assert scoring.band_for(bands, 25) == "critical"


def test_band_ranges_cover_every_score_without_overlap() -> None:
    bands = scoring.default_bands(25)
    ranges = scoring.band_ranges(bands, 25)
    covered = [s for lo, hi in ranges.values() for s in range(lo, hi + 1)]
    assert sorted(covered) == list(range(1, 26))


def test_rescale_keeps_relative_position() -> None:
    assert scoring.rescale(5, 3) == 3
    assert scoring.rescale(1, 3) == 1
    assert scoring.rescale(3, 5) == 3
    assert scoring.rescale(4, 4) == 3
    assert all(1 <= scoring.rescale(v, n) <= n for v in range(1, 6) for n in range(3, 7))


def test_default_scales_label_every_level() -> None:
    for levels in range(MIN_LEVELS, MAX_LEVELS + 1):
        for kind in ("likelihood", "impact"):
            scale = scoring.default_scale(kind, levels)
            assert [s["level"] for s in scale] == list(range(1, levels + 1))
            assert all(s["label"] for s in scale)


def test_validate_bands_refuses_a_descending_or_oversized_threshold() -> None:
    good = scoring.default_bands(25)
    assert scoring.validate_bands(good, 25)[0]["min_score"] == 1
    descending = [dict(b) for b in good]
    descending[2]["min_score"] = 4
    with pytest.raises(InvalidInput):
        scoring.validate_bands(descending, 25)
    oversized = [dict(b) for b in good]
    oversized[3]["min_score"] = 30
    with pytest.raises(InvalidInput):
        scoring.validate_bands(oversized, 25)
    with pytest.raises(InvalidInput):
        scoring.validate_bands(good[:3], 25)


def test_validate_scale_needs_one_label_per_level() -> None:
    with pytest.raises(InvalidInput):
        scoring.validate_scale([{"label": "Low"}, {"label": "High"}], 3, axis="impact")
    with pytest.raises(InvalidInput):
        scoring.validate_scale([{"label": ""}] * 3, 3, axis="impact")


def test_accepted_is_never_a_manual_target_and_closed_only_reopens() -> None:
    for targets in scoring.STATUS_TRANSITIONS.values():
        assert "accepted" not in targets
    assert scoring.STATUS_TRANSITIONS["closed"] == ("open",)
    scoring.check_transition("open", "in_treatment")
    with pytest.raises(InvalidInput):
        scoring.check_transition("closed", "mitigated")


def test_import_headers_accept_the_template_labels_and_common_spellings() -> None:
    assert _normalise_header("Title *") == "title"
    assert _normalise_header("Sub-Category") == "sub_category"
    assert _normalise_header("Risk Owner") == "owner"
    assert _normalise_header("Department") == "business_unit"
    assert _normalise_header("Inherent Likelihood") == "inherent_likelihood"
    assert _normalise_header("Next review") == "next_review_on"


def test_import_cells_parse_numbers_dates_and_choices() -> None:
    row = ImportRow(row_number=2)
    assert _int("3", "Impact", row) == 3
    assert _int(4.0, "Impact", row) == 4
    assert _int("", "Impact", row) is None
    assert _int("high", "Impact", row) is None
    assert row.errors == ["Impact must be a number"]
    assert str(_date("2026-12-31", "Next review", row)) == "2026-12-31"
    assert _date("31/12/2026", "Next review", row) is None
    assert _choice("In treatment", {"in_treatment": "In treatment"}) == "in_treatment"
    assert _choice("unknown", {"open": "Open"}) == "?"


def test_csv_rows_skip_blanks_and_keep_spreadsheet_row_numbers() -> None:
    data = b"Title,Category\nPhishing,Technology\n,\nBackup failure,Technology\n"
    rows = read_rows("risks.csv", data)
    assert [n for n, _ in rows] == [2, 4]
    assert rows[0][1] == {"title": "Phishing", "category": "Technology"}
    with pytest.raises(InvalidInput):
        read_rows("risks.pdf", data)


def _templates() -> list[Any]:
    return [SimpleNamespace(**t) for t in json.loads(LIBRARY.read_text(encoding="utf-8"))]


def test_assist_matches_a_title_to_the_closest_library_risk() -> None:
    ranked = rank_templates(_templates(), "Ransomware encrypts our production servers", None)
    assert ranked
    assert "ransomware" in ranked[0][1].title.lower()


def test_assist_finds_nothing_for_an_unrelated_title() -> None:
    assert rank_templates(_templates(), "zzz qqq", None) == []


def test_the_shipped_library_uses_the_default_taxonomy() -> None:
    taxonomy = {name: set(children) for name, children in scoring.DEFAULT_TAXONOMY}
    for template in _templates():
        assert template.category in taxonomy, template.code
        assert template.sub_category in taxonomy[template.category], template.code
        assert 1 <= template.default_likelihood <= 5
        assert 1 <= template.default_impact <= 5
