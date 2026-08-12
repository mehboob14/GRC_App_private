"""Declarative conventions (docs/conventions/database.md)."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Index, MetaData, Table, Text, Uuid

from verity.db.base import (
    NAMING_CONVENTION,
    integration_unique,
    status_check,
    tenant_index,
)


def test_naming_convention_matches_the_documented_shape() -> None:
    assert NAMING_CONVENTION["ix"] == "ix_%(table_name)s__%(column_0_N_name)s"
    assert NAMING_CONVENTION["uq"] == "uq_%(table_name)s__%(column_0_N_name)s"
    assert NAMING_CONVENTION["ck"] == "ck_%(table_name)s__%(constraint_name)s"


def _index_columns(index: Index) -> list[str]:
    """The column names in order.

    An index built from names and not yet attached to a table holds them as strings,
    so this reads them without assuming they have been resolved to columns.
    """
    return [str(expression) for expression in index.expressions]


def test_tenant_index_leads_with_tenant_id() -> None:
    """The rule a query plan silently breaks: tenant_id is always first."""
    index = tenant_index("controls", "status", "owner_membership_id")
    assert _index_columns(index) == ["tenant_id", "status", "owner_membership_id"]
    assert index.name == "ix_controls__tenant_id_status_owner_membership_id"
    assert not index.unique


def test_tenant_index_can_be_unique() -> None:
    index = tenant_index("controls", "code", unique=True)
    assert index.unique
    assert index.name == "uq_controls__tenant_id_code"


def test_tenant_index_rejects_an_explicit_tenant_id() -> None:
    """Passing it is how it ends up second."""
    with pytest.raises(ValueError, match="always puts it first"):
        tenant_index("controls", "tenant_id", "status")


def test_tenant_index_rejects_an_empty_column_list() -> None:
    with pytest.raises(ValueError, match="at least one column"):
        tenant_index("controls")


@pytest.mark.parametrize("name", ["Controls", "control-statuses", "1controls", "drop table x"])
def test_helpers_reject_names_that_are_not_identifiers(name: str) -> None:
    with pytest.raises(ValueError, match="snake_case identifier"):
        tenant_index(name, "status")


def test_integration_unique_covers_tenant_source_and_external_id() -> None:
    """What makes every future connector an idempotent upsert."""
    constraint = integration_unique("assets")
    # A constraint built from column names resolves them when it is attached to a
    # table, so this attaches it to a throwaway one rather than reading a private
    # attribute off the unattached constraint.
    Table(
        "assets",
        MetaData(),
        Column("tenant_id", Uuid),
        Column("source", Text),
        Column("external_id", Text),
        constraint,
    )
    assert [column.name for column in constraint.columns] == [
        "tenant_id",
        "source",
        "external_id",
    ]
    assert constraint.name == "uq_assets__tenant_id_source_external_id"


def test_status_check_renders_a_check_constraint_not_an_enum() -> None:
    constraint = status_check("controls", "status", ["not_started", "implemented", "disabled"])
    rendered = str(constraint.sqltext.compile(compile_kwargs={"literal_binds": True}))
    assert constraint.name == "ck_controls__status_valid"
    assert "status IN" in rendered.replace("  ", " ")
    for value in ("not_started", "implemented", "disabled"):
        assert value in rendered


def test_status_check_rejects_an_empty_value_list() -> None:
    with pytest.raises(ValueError, match="at least one allowed value"):
        status_check("controls", "status", [])


def test_status_check_name_survives_attachment_to_a_convention_bearing_table() -> None:
    """The ``ck`` naming convention contains ``%(constraint_name)s``, so an explicit
    name that is not marked ``conv`` gets wrapped a second time at table-attach and
    comes out ``ck_controls__ck_controls__status_valid`` — a name the hand-written
    migration does not use, which autogenerate would then flag forever."""
    constraint = status_check("controls", "status", ["draft", "active"])
    Table(
        "controls",
        MetaData(naming_convention=NAMING_CONVENTION),
        Column("status", Text),
        constraint,
    )
    assert constraint.name == "ck_controls__status_valid"
