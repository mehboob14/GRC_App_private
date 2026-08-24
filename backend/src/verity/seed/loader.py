"""Load shipped global content (frameworks, requirements, control templates).

Global content is code, not customer data: it carries no ``tenant_id``, has no RLS,
and the application role holds only ``SELECT`` on it. The loader therefore runs on
the **migration/owner** connection, not the app pool.

Everything here keys on the *natural* key — ``frameworks.code``,
``requirements.requirement_key``, ``control_templates.code``, and the
``(template, requirement)`` pair — never on a generated UUID. That is the single
property the framework engine depends on: a content update mutates the same row,
so no crosswalk edge is ever orphaned. Re-minting ids on a re-seed would dangle
every mapping and every future readiness snapshot at once, across all tenants.

The pass is upsert + prune: rows present in the pack are inserted or updated in
place, rows no longer in the pack are deleted. Deletion is safe here precisely
because these tables are content — a requirement a framework no longer has should
not linger — and the FKs into them are ``ON DELETE RESTRICT``, so a prune that
would orphan tenant data fails loudly instead of silently cascading.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from verity.core.config import get_settings
from verity.core.logging import get_logger
from verity.modules.compliance.models import (
    ControlTemplate,
    Framework,
    FrameworkVersion,
    FrameworkVersionRequirement,
    Requirement,
    TemplateRequirementMap,
)
from verity.shared.ids import uuid7

logger = get_logger(__name__)

CONTENT_ROOT = Path(__file__).parent / "content"


@dataclass
class TableResult:
    """What one pass did to one table."""

    inserted: int = 0
    updated: int = 0
    pruned: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.inserted or self.updated or self.pruned)


@dataclass
class LoadResult:
    tables: dict[str, TableResult] = field(default_factory=dict)

    def table(self, name: str) -> TableResult:
        return self.tables.setdefault(name, TableResult())

    @property
    def changed(self) -> bool:
        return any(table.changed for table in self.tables.values())

    def summary(self) -> str:
        return " · ".join(
            f"{name} +{t.inserted}/~{t.updated}/-{t.pruned}"
            for name, t in sorted(self.tables.items())
        )


def _read(pack: Path, name: str) -> Any:  # noqa: ANN401 — a JSON document is Any by nature
    return json.loads((pack / name).read_text(encoding="utf-8"))


def _apply(row: object, values: dict[str, Any]) -> bool:
    """Copy ``values`` onto ``row``; return whether anything actually changed.

    The comparison matters: an unconditional assignment would mark every row dirty
    on every run, so "did the content change?" could never be answered.
    """
    changed = False
    for key, value in values.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    return changed


async def _load_framework(
    session: AsyncSession, doc: dict[str, Any], result: LoadResult
) -> tuple[Framework, FrameworkVersion]:
    """Upsert the framework and its version."""
    framework = (
        await session.execute(select(Framework).where(Framework.code == doc["code"]))
    ).scalar_one_or_none()
    fields = {"name": doc["name"], "description": doc.get("description"), "built_in": True}
    if framework is None:
        framework = Framework(id=uuid7(), code=doc["code"], **fields)
        session.add(framework)
        await session.flush([framework])
        result.table("frameworks").inserted += 1
    elif _apply(framework, fields):
        result.table("frameworks").updated += 1

    version = (
        await session.execute(
            select(FrameworkVersion).where(
                FrameworkVersion.framework_id == framework.id,
                FrameworkVersion.version == doc["version"],
            )
        )
    ).scalar_one_or_none()
    if version is None:
        version = FrameworkVersion(
            id=uuid7(),
            framework_id=framework.id,
            version=doc["version"],
            published_at=datetime.now(UTC),
            is_current=True,
        )
        session.add(version)
        await session.flush([version])
        result.table("framework_versions").inserted += 1
    elif _apply(version, {"is_current": True}):
        result.table("framework_versions").updated += 1

    return framework, version


async def _load_requirements(
    session: AsyncSession,
    framework: Framework,
    docs: Sequence[dict[str, Any]],
    result: LoadResult,
) -> dict[str, Requirement]:
    """Upsert requirements keyed on requirement_key; prune any the pack dropped."""
    existing = {
        row.requirement_key: row
        for row in (
            await session.execute(
                select(Requirement).where(Requirement.framework_id == framework.id)
            )
        ).scalars()
    }
    by_key: dict[str, Requirement] = {}
    for doc in docs:
        key = doc["requirement_key"]
        values = {
            "code": doc["code"],
            "category": doc["category"],
            "trust_services_category": doc["trust_services_category"],
            "name": doc["name"],
            "description": doc.get("description"),
            "is_always_in_scope": doc["is_always_in_scope"],
        }
        row = existing.pop(key, None)
        if row is None:
            row = Requirement(id=uuid7(), framework_id=framework.id, requirement_key=key, **values)
            session.add(row)
            await session.flush([row])
            result.table("requirements").inserted += 1
        elif _apply(row, values):
            result.table("requirements").updated += 1
        by_key[key] = row

    for stale in existing.values():
        await session.delete(stale)
        result.table("requirements").pruned += 1
    return by_key


async def _load_version_membership(
    session: AsyncSession,
    version: FrameworkVersion,
    requirements: dict[str, Requirement],
    result: LoadResult,
) -> None:
    """Pin exactly this version's requirement set — readiness computes against it."""
    members = {
        row.requirement_id
        for row in (
            await session.execute(
                select(FrameworkVersionRequirement).where(
                    FrameworkVersionRequirement.framework_version_id == version.id
                )
            )
        ).scalars()
    }
    for requirement in requirements.values():
        if requirement.id in members:
            members.discard(requirement.id)
            continue
        session.add(
            FrameworkVersionRequirement(
                framework_version_id=version.id, requirement_id=requirement.id
            )
        )
        result.table("framework_version_requirements").inserted += 1
    if members:
        await session.execute(
            delete(FrameworkVersionRequirement).where(
                FrameworkVersionRequirement.framework_version_id == version.id,
                FrameworkVersionRequirement.requirement_id.in_(members),
            )
        )
        result.table("framework_version_requirements").pruned += len(members)


async def _load_templates(
    session: AsyncSession, docs: Sequence[dict[str, Any]], result: LoadResult
) -> tuple[dict[str, ControlTemplate], dict[str, ControlTemplate]]:
    """Upsert control templates keyed on ``canonical_key``.

    Keyed on canonical_key, not code: the code is a label the pack may restyle
    (the 2026-08 re-code to category codes did exactly that), while
    canonical_key is the identity the pack was authored against. Keying on code
    would read a re-coded template as "new one, old one dropped" and try to
    delete a row that adopted tenant controls still reference.

    Returns ``(current, stale)`` — keyed by the pack's *code* for the crosswalk,
    which names templates by code. Stale templates are handed back rather than
    deleted here: the crosswalk rows pointing at them must go first, or the
    ``RESTRICT`` foreign key refuses the delete.
    """
    existing = {
        row.canonical_key: row for row in (await session.execute(select(ControlTemplate))).scalars()
    }
    by_code: dict[str, ControlTemplate] = {}
    for doc in docs:
        values = {
            "code": doc["code"],
            "name": doc["name"],
            "category": doc["category"],
            # Optional by design: shipped framework content asserts no
            # Preventive/Detective/Corrective classification.
            "control_type": doc.get("control_type"),
            "control_sub_type": doc.get("control_sub_type"),
            "importance": doc["importance"],
            "description": doc["description"],
            "implementation_guidance": doc.get("implementation_guidance"),
            "built_in": True,
        }
        row = existing.pop(doc["canonical_key"], None)
        if row is None:
            row = ControlTemplate(id=uuid7(), canonical_key=doc["canonical_key"], **values)
            session.add(row)
            await session.flush([row])
            result.table("control_templates").inserted += 1
        elif _apply(row, values):
            result.table("control_templates").updated += 1
        by_code[doc["code"]] = row
    return by_code, existing


async def _load_crosswalk(
    session: AsyncSession,
    docs: Sequence[dict[str, Any]],
    templates: dict[str, ControlTemplate],
    requirements: dict[str, Requirement],
    result: LoadResult,
) -> None:
    """Upsert the shipped template->requirement crosswalk."""
    wanted = {
        (templates[d["template_code"]].id, requirements[d["requirement_key"]].id) for d in docs
    }
    existing = {
        (row.template_id, row.requirement_id): row
        for row in (await session.execute(select(TemplateRequirementMap))).scalars()
    }
    for template_id, requirement_id in wanted - set(existing):
        session.add(
            TemplateRequirementMap(
                id=uuid7(), template_id=template_id, requirement_id=requirement_id
            )
        )
        result.table("template_requirement_map").inserted += 1
    for pair in set(existing) - wanted:
        await session.delete(existing[pair])
        result.table("template_requirement_map").pruned += 1


async def load_pack(session: AsyncSession, pack: Path) -> LoadResult:
    """Load one content pack directory. Idempotent: a second run changes nothing."""
    result = LoadResult()
    framework, version = await _load_framework(session, _read(pack, "framework.json"), result)
    requirements = await _load_requirements(
        session, framework, _read(pack, "requirements.json"), result
    )
    await _load_version_membership(session, version, requirements, result)
    templates, stale_templates = await _load_templates(
        session, _read(pack, "control_templates.json"), result
    )
    await _load_crosswalk(
        session, _read(pack, "template_requirements.json"), templates, requirements, result
    )
    # Only now can a dropped template go: its crosswalk rows are deleted above.
    await session.flush()
    for stale in stale_templates.values():
        await session.delete(stale)
        result.table("control_templates").pruned += 1
    await session.flush()
    return result


async def load_all(packs: Sequence[Path] | None = None) -> LoadResult:
    """Load every content pack on the **owner** connection, in one transaction.

    The app role holds SELECT only on these tables (see the global-content
    migration), so this deliberately does not use the application engine.
    """
    engine = create_async_engine(get_settings().database.effective_migration_url)
    combined = LoadResult()
    try:
        maker = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with maker() as session, session.begin():
            for pack in packs or sorted(p for p in CONTENT_ROOT.iterdir() if p.is_dir()):
                one = await load_pack(session, pack)
                for name, table in one.tables.items():
                    total = combined.table(name)
                    total.inserted += table.inserted
                    total.updated += table.updated
                    total.pruned += table.pruned
    finally:
        await engine.dispose()

    logger.info("seed.content.loaded", summary=combined.summary(), changed=combined.changed)
    return combined
