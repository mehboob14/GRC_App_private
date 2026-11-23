"""Thirteen SOC 2 mapping additions from the guided onboarding review (part 5 section 7, D-10).

The owner decided on 2026-11-23 to apply them with a notice to existing workspaces and an audit
row per change. The shipped crosswalk (``template_requirements.json``) carries them for new
workspaces through ``seed-content``; this migration carries them to controls a workspace already
adopted, under the library-update rule (CF-6): a control is changed only if its SOC 2 mapping is
still exactly what was shipped. One a workspace has edited is left alone.

Each added link gets an audit row (actor: system). Each workspace that changed is told through a
``library_update`` notification to its security lead, executive sponsor and the owners of the
controls that changed. DM-14 moving from full to partial on P8.1 changes only the shipped
coverage, which lives in global content, so nothing here touches it.

Forced RLS filters the owner's statements too, so it is lifted for the backfill and restored in
the same transaction, as the earlier content migrations do.

Revision ID: 6a1f9d3c8e25
Revises: 5d2f8a1c7b63
Create Date: 2026-11-23
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.naming import conv

revision: str = "6a1f9d3c8e25"
down_revision: str | None = "5d2f8a1c7b63"
branch_labels: str | None = None
depends_on: str | None = None

# code -> (SOC 2 criteria as shipped before, as shipped now)
CHANGES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "IAM-08": (("CC6.1", "CC6.3"), ("CC5.2", "CC6.1", "CC6.3")),
    "SD-01": (("CC8.1",), ("CC5.2", "CC8.1")),
    "NS-04": (("CC6.1", "CC7.1"), ("CC5.2", "CC6.1", "CC7.1")),
    "IAM-09": (("CC6.3",), ("CC5.1", "CC6.3")),
    "DM-06": (("C1.1",), ("C1.1", "CC2.1")),
    "DM-04": (("C1.1",), ("C1.1", "CC2.1")),
    "PE-01": (("CC6.4", "CC9.2"), ("A1.2", "CC6.4", "CC9.2")),
    "GOV-13": (("CC4.1",), ("CC4.1", "P8.1")),
    "DM-09": (("P6.1", "P6.2"), ("P6.1", "P6.2", "P6.7")),
    "LM-07": (("CC7.4",), ("CC7.4", "P6.5")),
    "DM-08": (("C1.2", "P4.2"), ("C1.2", "P4.2", "PI1.5")),
    "BC-01": (("A1.2", "CC9.1"), ("A1.2", "CC9.1", "PI1.5")),
    "CS-02": (("CC2.3",), ("CC2.3", "PI1.1")),
}

_KINDS_BEFORE: tuple[str, ...] = (
    "assigned",
    "comment",
    "status",
    "sla_breach",
    "sla_due",
    "approval",
    "recurrence",
    "vendor_reassessment_due",
    "vendor_document_expiring",
    "risk_acceptance_requested",
    "risk_acceptance_decided",
    "risk_acceptance_expired",
    "risk_review_due",
    "document_review_due",
    "document_review_overdue",
    "document_ack_reminder",
)
_KINDS_AFTER: tuple[str, ...] = (*_KINDS_BEFORE, "library_update")
_TABLES = ("controls", "control_requirements", "audit_log", "notifications", "owner_functions")
_TEXT_ARRAY = postgresql.ARRAY(sa.Text())

# Template controls whose SOC 2 mapping is exactly ``keys``. Other frameworks' links are ignored,
# so a workspace that also runs ISO 27001 still gets the correction.
_UNEDITED = sa.text(
    "SELECT c.id, c.tenant_id, c.owner_membership_id FROM controls c "
    "JOIN control_templates t ON t.id = c.template_id "
    "WHERE t.code = :code AND c.origin = 'template' AND c.disabled_at IS NULL "
    "AND COALESCE(("
    "  SELECT array_agg(r.requirement_key ORDER BY r.requirement_key) "
    "  FROM control_requirements cr JOIN requirements r ON r.id = cr.requirement_id "
    "  WHERE cr.control_id = c.id AND r.requirement_key LIKE 'SOC2:%'), ARRAY[]::text[]) = :keys"
).bindparams(sa.bindparam("keys", type_=_TEXT_ARRAY))

_REQUIREMENT = sa.text("SELECT id FROM requirements WHERE requirement_key = :key")
_HAS = sa.text(
    "SELECT 1 FROM control_requirements WHERE control_id = :control_id AND requirement_id = :rid"
)
_ADD = sa.text(
    "INSERT INTO control_requirements (id, tenant_id, control_id, requirement_id) "
    "VALUES (:id, :tenant_id, :control_id, :rid)"
)
_REMOVE = sa.text(
    "DELETE FROM control_requirements WHERE control_id = :control_id AND requirement_id = :rid"
)
_AUDIT = sa.text(
    "INSERT INTO audit_log (id, tenant_id, actor_type, actor_id, action, object_type, object_id, "
    "before, after) VALUES (:id, :tenant_id, 'system', NULL, :action, 'control_requirement', "
    ":object_id, CAST(:before AS jsonb), CAST(:after AS jsonb))"
)
_HOLDERS = sa.text(
    "SELECT membership_id FROM owner_functions WHERE tenant_id = :tenant_id "
    "AND function_key IN ('security_lead', 'executive_sponsor') AND membership_id IS NOT NULL"
)
_NOTIFY = sa.text(
    "INSERT INTO notifications (id, tenant_id, recipient_membership_id, kind, title, body) "
    "VALUES (:id, :tenant_id, :recipient, 'library_update', :title, :body)"
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def _set_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(conv("ck_notifications__kind_valid"), "notifications", type_="check")
    op.create_check_constraint(
        conv("ck_notifications__kind_valid"), "notifications", _in("kind", kinds)
    )


def _keys(criteria: tuple[str, ...]) -> list[str]:
    return sorted(f"SOC2:{c}" for c in criteria)


def _apply(forward: bool) -> None:
    bind = op.get_bind()
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    try:
        changed: dict[uuid.UUID, list[tuple[str, str]]] = defaultdict(list)
        owners: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for code, (before, after) in CHANGES.items():
            source = before if forward else after
            delta = sorted(set(after) - set(before))
            for control_id, tenant_id, owner in bind.execute(
                _UNEDITED, {"code": code, "keys": _keys(source)}
            ).all():
                for criterion in delta:
                    rid = bind.execute(_REQUIREMENT, {"key": f"SOC2:{criterion}"}).scalar()
                    if rid is None:
                        continue
                    present = bind.execute(_HAS, {"control_id": control_id, "rid": rid}).first()
                    if forward and present is None:
                        link = uuid.uuid4()
                        bind.execute(
                            _ADD,
                            {
                                "id": link,
                                "tenant_id": tenant_id,
                                "control_id": control_id,
                                "rid": rid,
                            },
                        )
                        record = {"control": code, "requirement": f"SOC2:{criterion}"}
                        bind.execute(
                            _AUDIT,
                            {
                                "id": uuid.uuid4(),
                                "tenant_id": tenant_id,
                                "action": "create",
                                "object_id": link,
                                "before": None,
                                "after": json.dumps({**record, "reason": "library update D-10"}),
                            },
                        )
                        changed[tenant_id].append((code, criterion))
                        if owner is not None:
                            owners[tenant_id].add(owner)
                    elif not forward and present is not None:
                        bind.execute(_REMOVE, {"control_id": control_id, "rid": rid})
        for tenant_id, pairs in changed.items():
            recipients = {row[0] for row in bind.execute(_HOLDERS, {"tenant_id": tenant_id})}
            recipients |= owners[tenant_id]
            body = (
                "These controls now also count for: "
                + "; ".join(f"{code} for {criterion}" for code, criterion in sorted(pairs))
                + ". Controls you edited were left as they were."
            )
            for recipient in recipients:
                bind.execute(
                    _NOTIFY,
                    {
                        "id": uuid.uuid4(),
                        "tenant_id": tenant_id,
                        "recipient": recipient,
                        "title": "Control mappings updated",
                        "body": body[:2000],
                    },
                )
    finally:
        for table in _TABLES:
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _set_kinds(_KINDS_AFTER)
    _apply(forward=True)


def downgrade() -> None:
    _apply(forward=False)
    op.execute("ALTER TABLE notifications NO FORCE ROW LEVEL SECURITY")
    op.execute("DELETE FROM notifications WHERE kind = 'library_update'")
    op.execute("ALTER TABLE notifications FORCE ROW LEVEL SECURITY")
    _set_kinds(_KINDS_BEFORE)
