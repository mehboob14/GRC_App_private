"""The policy predicate the whole isolation story rests on, and the append-only DDL."""

from __future__ import annotations

import pytest

from verity.core.rls import TENANT_ID_SETTING
from verity.db.rls import (
    APPEND_ONLY_FUNCTION_NAME,
    append_only_function_ddl,
    append_only_trigger_ddl,
    append_only_trigger_name,
    tenant_policy_predicate,
)


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


# ---------------------------------------------------------------------------
# Append-only: the trigger half of make_append_only, as designed in the
# add-audit-trail change under "Append-only enforcement".
# ---------------------------------------------------------------------------


def test_the_guard_function_is_created_idempotently() -> None:
    """Every append-only migration emits it; the second emit must be a no-op."""
    assert append_only_function_ddl().startswith(
        f"CREATE OR REPLACE FUNCTION {APPEND_ONLY_FUNCTION_NAME}() RETURNS trigger"
    )


def test_the_guard_function_names_the_append_only_rule() -> None:
    ddl = append_only_function_ddl()
    assert "RAISE EXCEPTION" in ddl
    assert "append-only" in ddl
    assert "docs/conventions/database.md" in ddl


def test_the_guard_function_is_table_agnostic() -> None:
    """One shared function serves every append-only table, so the message must name
    the table dynamically rather than baking one in."""
    assert "TG_TABLE_NAME" in append_only_function_ddl()
    assert "TG_OP" in append_only_function_ddl()


def test_the_trigger_name_follows_the_convention() -> None:
    assert append_only_trigger_name("audit_log") == "trg_audit_log__append_only"


def test_the_trigger_fires_before_update_or_delete_per_row() -> None:
    ddl = append_only_trigger_ddl("audit_log")
    assert "BEFORE UPDATE OR DELETE ON audit_log" in ddl
    assert "FOR EACH ROW" in ddl
    assert f"EXECUTE FUNCTION {APPEND_ONLY_FUNCTION_NAME}()" in ddl


def test_the_trigger_is_replaced_rather_than_duplicated() -> None:
    assert append_only_trigger_ddl("audit_log").startswith(
        "CREATE OR REPLACE TRIGGER trg_audit_log__append_only "
    )


@pytest.mark.parametrize("table", ["Audit_Log", "audit-log", "audit_log; DROP TABLE x", ""])
def test_the_trigger_ddl_rejects_anything_that_is_not_an_identifier(table: str) -> None:
    with pytest.raises(ValueError, match="snake_case identifier"):
        append_only_trigger_ddl(table)
    with pytest.raises(ValueError, match="snake_case identifier"):
        append_only_trigger_name(table)
