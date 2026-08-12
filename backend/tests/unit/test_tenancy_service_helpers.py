"""The tenancy service's pure parts: recovery codes and the register's cursor."""

from __future__ import annotations

import uuid

import pytest

from verity.core.errors import InvalidInput
from verity.modules.tenancy.service import (
    consume_recovery_code,
    decode_tenant_cursor,
    encode_tenant_cursor,
    generate_recovery_codes,
    hash_recovery_codes,
)


def test_recovery_codes_are_distinct_and_phone_readable() -> None:
    codes = generate_recovery_codes()
    assert len(codes) == 8
    assert len(set(codes)) == 8
    for code in codes:
        head, _, tail = code.partition("-")
        assert len(head) == len(tail) == 5
        assert not set(code) & set("01OIl"), "ambiguous characters do not survive a phone call"


def test_a_recovery_code_is_consumed_by_the_check_that_accepts_it() -> None:
    codes = generate_recovery_codes(3)
    hashes = hash_recovery_codes(codes)

    remaining = consume_recovery_code(hashes, codes[1])
    assert remaining is not None
    assert len(remaining) == 2
    assert consume_recovery_code(remaining, codes[1]) is None, "single-use means gone"
    assert consume_recovery_code(remaining, codes[0]) is not None, "the others survive"


def test_a_wrong_recovery_code_consumes_nothing() -> None:
    hashes = hash_recovery_codes(generate_recovery_codes(2))
    assert consume_recovery_code(hashes, "wrong-wrong") is None
    assert len(hashes) == 2


def test_the_stored_form_is_a_hash_not_the_code() -> None:
    codes = generate_recovery_codes(1)
    hashes = hash_recovery_codes(codes)
    assert codes[0] not in hashes[0]
    assert hashes[0].startswith("$argon2id$")


def test_the_tenant_cursor_round_trips_and_stays_opaque() -> None:
    tenant_id = uuid.uuid4()
    cursor = encode_tenant_cursor(tenant_id)
    assert str(tenant_id) not in cursor
    assert decode_tenant_cursor(cursor) == tenant_id


@pytest.mark.parametrize("cursor", ["", "not-base64!", "bm90LWEtdXVpZA=="])
def test_a_malformed_cursor_is_invalid_input(cursor: str) -> None:
    with pytest.raises(InvalidInput):
        decode_tenant_cursor(cursor)
