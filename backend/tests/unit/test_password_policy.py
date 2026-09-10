"""The password policy checker, against the rules a tenant can actually set.

No database: the policy is a pure function of (password, policy) and the reuse
check is a pure function of (credentials row, password, depth). What is asserted
here is that a workspace cannot configure its way *below* the platform floor,
that every unmet rule is reported in one pass, and that "do not reuse the last
N" includes the password currently in force.
"""

from __future__ import annotations

import pytest

from verity.core.security import hash_password
from verity.modules.iam.exceptions import WeakPassword
from verity.modules.iam.models import Credentials
from verity.modules.iam.service import (
    MIN_PASSWORD_LENGTH,
    PasswordPolicy,
    assert_not_reused,
    rotate_password_history,
    validate_password,
)

STRONG = "Str0ng!Passphrase"


def test_the_default_policy_accepts_a_strong_password() -> None:
    validate_password(STRONG)


@pytest.mark.parametrize(
    ("password", "missing"),
    [
        ("Sh0rt!", "characters"),
        ("nouppercase1!", "uppercase"),
        ("NOLOWERCASE1!", "lowercase"),
        ("NoDigitsHere!!", "digit"),
        ("NoSymbolsHere11", "special character"),
    ],
)
def test_each_rule_is_enforced_and_named(password: str, missing: str) -> None:
    with pytest.raises(WeakPassword) as raised:
        validate_password(password)
    assert missing in str(raised.value.message)
    assert raised.value.code == "weak_password"


def test_every_unmet_rule_is_reported_in_one_pass() -> None:
    """Fixing one rule at a time, one request at a time, is the failure mode."""
    with pytest.raises(WeakPassword) as raised:
        validate_password("short")
    message = str(raised.value.message)
    for expected in ("characters", "uppercase", "digit", "special character"):
        assert expected in message


def test_a_relaxed_policy_still_cannot_go_below_the_platform_floor() -> None:
    """A tenant may be stricter than the platform, never weaker."""
    relaxed = PasswordPolicy(
        min_length=1,
        require_upper=False,
        require_lower=False,
        require_digit=False,
        require_symbol=False,
    )
    assert relaxed.effective_min_length == MIN_PASSWORD_LENGTH
    validate_password("a" * MIN_PASSWORD_LENGTH, relaxed)
    with pytest.raises(WeakPassword):
        validate_password("a" * (MIN_PASSWORD_LENGTH - 1), relaxed)


def test_a_stricter_policy_is_honoured() -> None:
    strict = PasswordPolicy(min_length=20)
    with pytest.raises(WeakPassword):
        validate_password(STRONG, strict)
    validate_password("Str0ng!Passphrase-Extended", strict)


def test_reuse_check_includes_the_password_currently_in_force() -> None:
    """The current hash is not in the history list until it is replaced, so a
    naive check over history alone would wave through "change it to itself"."""
    credentials = Credentials(user_id=None, password_hash=hash_password(STRONG))
    with pytest.raises(WeakPassword) as raised:
        assert_not_reused(credentials, STRONG, depth=5)
    assert "last 5" in str(raised.value.message)


def test_reuse_check_walks_the_history_and_respects_depth() -> None:
    old = "0ld!Passphrase-One"
    credentials = Credentials(
        user_id=None,
        password_hash=hash_password(STRONG),
        previous_password_hashes=[hash_password(old)],
    )
    with pytest.raises(WeakPassword):
        assert_not_reused(credentials, old, depth=5)

    # depth 1 covers only the password in force, so the older one is free again.
    assert_not_reused(credentials, old, depth=1)
    # depth 0 disables the check entirely.
    assert_not_reused(credentials, STRONG, depth=0)


def test_rotation_pushes_newest_first_and_trims_to_depth() -> None:
    credentials = Credentials(
        user_id=None,
        password_hash="hash-current",  # noqa: S106 — a marker string, not a secret
        previous_password_hashes=["hash-1", "hash-2"],
    )
    rotate_password_history(credentials, depth=2)
    assert credentials.previous_password_hashes == ["hash-current", "hash-1"]

    rotate_password_history(credentials, depth=0)
    assert credentials.previous_password_hashes is None
