"""UUIDv7 properties (ADR-0002)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from verity.shared.ids import uuid7, uuid7_timestamp


def test_version_and_variant_match_rfc_9562() -> None:
    value = uuid7()
    assert value.version == 7
    # Variant bits must be 0b10. `uuid` exposes this as RFC_4122, which RFC 9562
    # supersedes without changing the variant encoding.
    assert value.variant == uuid.RFC_4122


def test_identifiers_are_unique() -> None:
    values = {uuid7() for _ in range(10_000)}
    assert len(values) == 10_000


def test_identifiers_sort_in_generation_order() -> None:
    """The property the whole choice of v7 exists for.

    Cursor pagination and B-tree locality both depend on it, and v4 does not have it.
    """
    values = [uuid7() for _ in range(5_000)]
    assert values == sorted(values)


def test_monotonic_within_a_single_millisecond() -> None:
    """Generated fast enough to land in the same millisecond, still ordered.

    Without the counter in ``rand_a``, identifiers minted in the same millisecond order
    randomly, and "created_at, id" pagination skips or repeats rows.
    """
    values = [uuid7() for _ in range(2_000)]
    timestamps = {uuid7_timestamp(value) for value in values}
    assert len(timestamps) < len(values), "test did not exercise the same-millisecond path"
    assert values == sorted(values)


def test_timestamp_is_recent_and_utc() -> None:
    before = datetime.now(UTC)
    encoded = uuid7_timestamp(uuid7())
    after = datetime.now(UTC)
    assert encoded.tzinfo is UTC
    # Truncated to the millisecond, so allow the boundary either side.
    assert before.timestamp() - 0.001 <= encoded.timestamp() <= after.timestamp() + 0.001


def test_timestamp_rejects_other_uuid_versions() -> None:
    with pytest.raises(ValueError, match="version 7"):
        uuid7_timestamp(uuid.uuid4())
