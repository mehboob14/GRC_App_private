"""How a check's evidence is named, and how a repeat is told from a new result."""

from __future__ import annotations

import uuid
from typing import Any

from verity.modules.connectors.models import CheckResult
from verity.modules.connectors.service import _external_id, _filed_digest, _rows_digest, _slug
from verity.modules.evidence.service import series_of
from verity.shared.ids import uuid7


def _row(resource: str, outcome: str, **detail: Any) -> CheckResult:  # noqa: ANN401 — a result's detail
    return CheckResult(
        id=uuid7(),
        tenant_id=uuid7(),
        run_id=uuid7(),
        connection_id=uuid7(),
        check_id=uuid7(),
        resource_type="repository",
        resource_id=resource,
        resource_name=f"acme/{resource}",
        outcome=outcome,
        detail=detail,
    )


def test_what_a_check_found_has_one_digest_whatever_order_it_was_read_in() -> None:
    api, web = _row("api", "pass", summary="on"), _row("web", "fail", summary="off")
    assert _rows_digest([api, web]) == _rows_digest([web, api])


def test_a_changed_outcome_or_detail_is_a_different_digest() -> None:
    base = _rows_digest([_row("api", "pass", summary="on")])
    assert _rows_digest([_row("api", "fail", summary="on")]) != base
    assert _rows_digest([_row("api", "pass", summary="on", reviewers=["carol"])]) != base


def test_the_id_a_check_is_filed_under_gives_back_its_digest() -> None:
    connection, run = uuid.uuid4(), uuid.uuid4()
    digest = "ab" * 32
    filed = _external_id(connection, "vcs.secret_scanning_enabled", digest, run)
    assert filed.startswith(_external_id(connection, "vcs.secret_scanning_enabled"))
    assert _filed_digest(filed) == digest[:16]
    # Another check on the same connection never matches this check's prefix.
    assert not filed.startswith(_external_id(connection, "vcs.review_required"))


def test_an_id_of_another_shape_is_never_taken_for_a_repeat() -> None:
    assert _filed_digest("something-else") is None
    assert _filed_digest("a:b:c") is None


def test_a_check_key_makes_a_file_name_part() -> None:
    assert _slug("vcs.secret_scanning_enabled") == "vcs-secret-scanning-enabled"


def test_every_file_a_check_has_filed_belongs_to_one_series() -> None:
    connection = uuid.uuid4()
    first = _external_id(connection, "vcs.review_required", "ab" * 32, uuid.uuid4())
    later = _external_id(connection, "vcs.review_required", "cd" * 32, uuid.uuid4())
    other = _external_id(connection, "vcs.secret_scanning_enabled", "ab" * 32, uuid.uuid4())
    assert series_of("github", first) == series_of("github", later)
    assert series_of("github", first) != series_of("github", other)
    assert series_of("github", first) == _external_id(connection, "vcs.review_required").rstrip(":")


def test_an_item_with_no_source_or_no_connector_id_has_no_series() -> None:
    assert series_of(None, "c:k:d:r") is None
    assert series_of("github", None) is None
    assert series_of("github", "just-an-id") is None
    assert series_of("github", "two:parts") is None
