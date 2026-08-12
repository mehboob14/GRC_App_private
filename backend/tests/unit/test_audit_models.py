"""The ``AuditLog`` model: ORM append-only listeners and migration agreement.

The listeners are the third layer of append-only enforcement — the one that catches a
mutation in a unit test with no database, while the developer is still looking at it.
The database-backed layers (revoked grant, trigger) are proven in
``tests/integration/test_append_only.py``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Table, event

from verity.core.errors import VerityError
from verity.modules.audit.models import (
    ACTOR_TYPES,
    AUDIT_ACTIONS,
    AuditLog,
    AuditLogAppendOnlyError,
    refuse_orm_delete,
    refuse_orm_update,
)


def _table() -> Table:
    """``__table__`` is typed as the wider ``FromClause``; narrow it once."""
    table = AuditLog.__table__
    assert isinstance(table, Table)
    return table


# ---------------------------------------------------------------------------
# The listeners: registered on the mapper, and raising when they fire
# ---------------------------------------------------------------------------


def test_the_update_listener_is_registered_on_the_model() -> None:
    assert event.contains(AuditLog, "before_update", refuse_orm_update)


def test_the_delete_listener_is_registered_on_the_model() -> None:
    assert event.contains(AuditLog, "before_delete", refuse_orm_delete)


def test_the_update_listener_raises_naming_the_append_only_rule() -> None:
    with pytest.raises(AuditLogAppendOnlyError, match="append-only") as raised:
        refuse_orm_update(object(), object(), object())
    assert "UPDATE" in str(raised.value)


def test_the_delete_listener_raises_naming_the_append_only_rule() -> None:
    with pytest.raises(AuditLogAppendOnlyError, match="append-only") as raised:
        refuse_orm_delete(object(), object(), object())
    assert "DELETE" in str(raised.value)


def test_the_append_only_error_is_a_defect_not_a_domain_condition() -> None:
    """Like ``TenantContextError``: it must surface as a generic 500, never as a
    machine-readable code a client could branch on."""
    assert not issubclass(AuditLogAppendOnlyError, VerityError)


# ---------------------------------------------------------------------------
# The model's metadata matches the hand-written migration exactly, so a future
# autogenerate diffs nothing. The check names are the regression surface: the ck
# naming convention wraps an explicit name unless it is marked conv().
# ---------------------------------------------------------------------------


def test_the_table_shape_matches_the_documented_exception() -> None:
    columns = set(_table().columns.keys())
    assert columns == {
        "id",
        "tenant_id",
        "actor_type",
        "actor_id",
        "action",
        "object_type",
        "object_id",
        "before",
        "after",
        "occurred_at",
    }
    # The documented exception (docs/conventions/database.md): an updated_at on a
    # table that refuses UPDATE could only ever repeat occurred_at.
    assert "created_at" not in columns
    assert "updated_at" not in columns


def test_nullability_encodes_the_stream_and_actor_semantics() -> None:
    table = _table()
    assert table.columns["tenant_id"].nullable, "NULL tenant_id = provider plane"
    assert table.columns["actor_id"].nullable, "NULL actor_id = system actor"
    assert not table.columns["occurred_at"].nullable
    assert not any(table.columns["tenant_id"].foreign_keys), "no FK, by design"
    assert not any(table.columns["actor_id"].foreign_keys), "polymorphic, no FK"


def test_check_constraint_names_match_the_migration() -> None:
    names = {constraint.name for constraint in _table().constraints}
    assert {
        "ck_audit_log__actor_type_valid",
        "ck_audit_log__action_valid",
        "ck_audit_log__system_actor_has_no_actor_id",
        "pk_audit_log",
    } <= names
    doubled = {name for name in names if str(name).count("ck_audit_log__") > 1}
    assert not doubled, f"naming convention wrapped an explicit name: {doubled}"


def test_index_names_match_the_migration_and_lead_with_tenant_id() -> None:
    indexes = {index.name: index for index in _table().indexes}
    assert set(indexes) == {
        "ix_audit_log__tenant_id_occurred_at",
        "ix_audit_log__tenant_id_object_type_object_id",
        "ix_audit_log__tenant_id_actor_id",
    }
    for index in indexes.values():
        first = str(index.expressions[0])
        assert first.endswith("tenant_id"), f"{index.name} does not lead with tenant_id"


def test_the_action_and_actor_vocabularies_match_the_er_design() -> None:
    assert AUDIT_ACTIONS == ("create", "update", "delete", "transition", "approve")
    assert ACTOR_TYPES == ("membership", "platform_admin", "system")
