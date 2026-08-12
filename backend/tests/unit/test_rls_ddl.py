"""The policy predicate the whole isolation story rests on."""

from __future__ import annotations

import pytest

from verity.core.rls import TENANT_ID_SETTING
from verity.db.rls import tenant_policy_predicate


def test_predicate_reads_the_documented_setting() -> None:
    assert TENANT_ID_SETTING == "app.tenant_id"
    assert TENANT_ID_SETTING in tenant_policy_predicate()


def test_predicate_tolerates_an_unset_setting() -> None:
    """``current_setting(name, true)`` returns NULL rather than raising.

    Without the second argument, the first query on a tenant table from a connection
    that has not bound a tenant raises ``unrecognized configuration parameter`` and
    surfaces to the caller as a 500 instead of an empty result.
    """
    assert f"current_setting('{TENANT_ID_SETTING}', true)" in tenant_policy_predicate()


def test_predicate_turns_an_empty_setting_into_null_before_casting() -> None:
    """``''::uuid`` raises; ``NULLIF`` makes "no tenant bound" mean "no rows"."""
    assert tenant_policy_predicate() == (
        f"tenant_id = NULLIF(current_setting('{TENANT_ID_SETTING}', true), '')::uuid"
    )


def test_predicate_accepts_an_alternate_column() -> None:
    assert tenant_policy_predicate("workspace_id").startswith("workspace_id = ")


@pytest.mark.parametrize("column", ["Tenant_Id", "tenant-id", "tenant_id; DROP TABLE x", ""])
def test_predicate_rejects_anything_that_is_not_an_identifier(column: str) -> None:
    """Identifiers cannot be bound parameters, so every one is validated first."""
    with pytest.raises(ValueError, match="snake_case identifier"):
        tenant_policy_predicate(column)
