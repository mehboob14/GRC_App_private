"""Retire the evidence connectors filed before each check had its own.

Until each check filed its own evidence, one run filed one file holding every check's
results, titled "GitHub <account>: automated test results" and linked to every control
any of those checks touched. That is the wrong shape of evidence: SD-11, which is judged
by secret scanning alone, held a file about branch protection too. Each check now files
its own file, linked only to the controls that check supports.

This unlinks the old files from the controls. They stay in the evidence library as
history and can still be opened and downloaded; nothing is deleted (rule 6), and each
unlink is written to the audit log against the control. Run it once, after the first run
on the new code has filed the per-check evidence, so no control is left without evidence
in between: a workspace with no per-check evidence yet is skipped, and a control that has
no per-check evidence of its own keeps the old file until it does.

    # from backend/, with the venv active
    python -m scripts.retire_legacy_connector_evidence           # what it would do
    python -m scripts.retire_legacy_connector_evidence --apply   # do it

Safe to re-run: a file with no control left is not touched again.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import exists, select

from verity.core.db import dispose_engine, provider_session_scope, session_scope

# Register every module's models on Base.metadata before the mapper resolves
# cross-module FKs. Same set the Alembic env imports (see backfill_adopt_soc2).
from verity.modules.audit import models as _audit_models  # noqa: F401
from verity.modules.audit.service import System
from verity.modules.compliance import models as _compliance_models  # noqa: F401
from verity.modules.evidence.models import Evidence, EvidenceControl
from verity.modules.evidence.service import evidence_service
from verity.modules.iam import models as _iam_models  # noqa: F401
from verity.modules.tenancy import models as _tenancy_models  # noqa: F401
from verity.modules.tenancy.models import Tenant

LEGACY_TITLE = ": automated test results"


async def _tenant_ids() -> list[uuid.UUID]:
    async with provider_session_scope() as session:
        return [row[0] for row in await session.execute(select(Tenant.id))]


async def main(apply: bool) -> None:
    tenant_ids = await _tenant_ids()
    print(f"{'retiring' if apply else 'checking'} {len(tenant_ids)} workspace(s)...")
    retired_total = 0
    for tenant_id in tenant_ids:
        async with session_scope(tenant_id=tenant_id) as session:
            filed_per_check = await session.scalar(
                select(
                    exists().where(
                        Evidence.tenant_id == tenant_id,
                        Evidence.source.is_not(None),
                        Evidence.external_id.is_not(None),
                    )
                )
            )
            legacy = (
                await session.execute(
                    select(Evidence.id, Evidence.title).where(
                        Evidence.tenant_id == tenant_id,
                        Evidence.source.is_(None),
                        Evidence.evidence_type == "configuration_export",
                        Evidence.source_label.endswith(" connector"),
                        Evidence.title.contains(LEGACY_TITLE),
                        # Only the ones still linked: a retired file is left alone.
                        exists().where(
                            EvidenceControl.tenant_id == tenant_id,
                            EvidenceControl.evidence_id == Evidence.id,
                        ),
                    )
                )
            ).all()
            if not legacy:
                continue
            if not filed_per_check:
                print(f"  {tenant_id}: {len(legacy)} old file(s), skipped: run the connection")
                continue
            # A control the new evidence has not reached yet keeps the old file: unlinking
            # it would leave the control with nothing.
            covered = set(
                (
                    await session.execute(
                        select(EvidenceControl.control_id)
                        .join(Evidence, Evidence.id == EvidenceControl.evidence_id)
                        .where(
                            EvidenceControl.tenant_id == tenant_id,
                            Evidence.tenant_id == tenant_id,
                            Evidence.source.is_not(None),
                        )
                    )
                ).scalars()
            )
            linked: dict[uuid.UUID, set[uuid.UUID]] = {}
            for evidence_id, control_id in (
                await session.execute(
                    select(EvidenceControl.evidence_id, EvidenceControl.control_id).where(
                        EvidenceControl.tenant_id == tenant_id,
                        EvidenceControl.evidence_id.in_([row.id for row in legacy]),
                    )
                )
            ).tuples():
                linked.setdefault(evidence_id, set()).add(control_id)
            for evidence_id, title in legacy:
                drop = linked.get(evidence_id, set()) & covered
                keep = linked.get(evidence_id, set()) - covered
                if not drop:
                    continue
                print(
                    f"  {tenant_id}: {title}: unlink {len(drop)} control(s)"
                    + (f", keep {len(keep)} with no new evidence yet" if keep else "")
                )
                if apply:
                    await evidence_service.map_controls(
                        session,
                        tenant_id=tenant_id,
                        evidence_id=evidence_id,
                        control_ids=sorted(keep),
                        replace=True,
                        actor=System(),
                        title=title,
                    )
                retired_total += 1
    verb = "unlinked" if apply else "would unlink"
    print(f"done: {verb} {retired_total} file(s)")
    if not apply and retired_total:
        print("run again with --apply to do it")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
