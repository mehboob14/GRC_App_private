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
import uuid
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
from verity.modules.connectors.models import Check, ControlTemplateCheck, IntegrationCapability
from verity.modules.documents.models import DocumentTemplate
from verity.modules.risk.models import RiskTemplate
from verity.modules.vendors.models import QuestionnaireQuestion, QuestionnaireTemplate
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


async def _load_document_templates(
    session: AsyncSession, docs: Sequence[dict[str, Any]], result: LoadResult
) -> None:
    """Upsert shipped policy templates, keyed on the pack's stable ``key``.

    A template dropped upstream is pruned: nothing references these rows once a
    document has been instantiated from one — the tenant's copy is independent
    by design — so removing a retired template cannot orphan anyone's policy.
    """
    existing = {row.key: row for row in (await session.execute(select(DocumentTemplate))).scalars()}
    for doc in docs:
        values = {
            "title": doc["title"],
            "doc_type": doc.get("doc_type", "policy"),
            "classification": doc.get("classification", "internal"),
            "summary": doc.get("summary"),
            "content_html": doc["content_html"],
            "tags": doc.get("tags") or [],
            "satisfies": doc.get("satisfies") or {},
            "placeholders": doc.get("placeholders") or [],
            "word_count": doc.get("word_count", 0),
            "optional_markers": doc.get("optional_markers", 0),
            "source": doc.get("source"),
            "source_url": doc.get("source_url"),
            "source_commit": doc.get("source_commit"),
            "license": doc.get("license"),
        }
        row = existing.pop(doc["key"], None)
        if row is None:
            session.add(DocumentTemplate(id=uuid7(), key=doc["key"], **values))
            result.table("document_templates").inserted += 1
        elif _apply(row, values):
            result.table("document_templates").updated += 1
    for stale in existing.values():
        await session.delete(stale)
        result.table("document_templates").pruned += 1
    await session.flush()


async def _load_questionnaire_bank(
    session: AsyncSession, payload: dict[str, Any], result: LoadResult
) -> None:
    """Upsert the vendor questionnaire bank, keyed on the stable ``code`` pair.

    A question is keyed on ``(template, code)`` and never on its prose, because a
    ``vendor_assessment_responses`` row points at the question it answered. Rewording
    a question in a later pack must move the same row, or every historical answer
    stops meaning anything.

    Retired questions are **not** pruned. That is the one place this differs from
    the other packs, and the FK enforces it: responses reference questions
    ``ON DELETE RESTRICT``, so a question somebody has answered cannot be deleted.
    A question dropped upstream stops being *asked* — the pack no longer lists it,
    so a new assessment never includes it — while the answers already given to it
    stay readable. Unasked and deleted are different things to an auditor.
    """
    template_row = (
        await session.execute(
            select(QuestionnaireTemplate).where(
                QuestionnaireTemplate.code == payload["template"]["code"]
            )
        )
    ).scalar_one_or_none()
    fields = {k: v for k, v in payload["template"].items() if k != "code"}
    if template_row is None:
        template_row = QuestionnaireTemplate(id=uuid7(), code=payload["template"]["code"], **fields)
        session.add(template_row)
        result.table("questionnaire_templates").inserted += 1
    elif _apply(template_row, fields):
        result.table("questionnaire_templates").updated += 1
    await session.flush()

    existing = {
        row.code: row
        for row in (
            await session.execute(
                select(QuestionnaireQuestion).where(
                    QuestionnaireQuestion.template_id == template_row.id
                )
            )
        ).scalars()
    }
    for question in payload["questions"]:
        values = {k: v for k, v in question.items() if k not in ("code", "parent_code")}
        row = existing.get(question["code"])
        if row is None:
            row = QuestionnaireQuestion(
                id=uuid7(),
                template_id=template_row.id,
                code=question["code"],
                **values,
            )
            session.add(row)
            existing[question["code"]] = row
            result.table("questionnaire_questions").inserted += 1
        elif _apply(row, values):
            result.table("questionnaire_questions").updated += 1
    await session.flush()

    # Branching names its parent by code, because the pack cannot know an id.
    # Only a pack that states parents is touched, so the core bank's rows keep
    # whatever they hold.
    for question in payload["questions"]:
        if "parent_code" not in question:
            continue
        parent = existing.get(question["parent_code"]) if question["parent_code"] else None
        row = existing[question["code"]]
        if _apply(row, {"parent_question_id": parent.id if parent else None}):
            result.table("questionnaire_questions").updated += 1
    await session.flush()


async def _load_risk_templates(
    session: AsyncSession, templates: Sequence[dict[str, Any]], result: LoadResult
) -> None:
    """Upsert the starter risk library, keyed on ``code``.

    A template dropped upstream is pruned. Adopted risks copied its text and keep
    only an ancestry pointer (``risks.template_id``, ``ON DELETE SET NULL``), so a
    retired template never changes a risk someone has reviewed.
    """
    existing = {row.code: row for row in (await session.execute(select(RiskTemplate))).scalars()}
    for item in templates:
        values = {
            "title": item["title"],
            "description": item.get("description", ""),
            "category": item["category"],
            "sub_category": item.get("sub_category"),
            "default_likelihood": item["default_likelihood"],
            "default_impact": item["default_impact"],
            "root_cause": item.get("root_cause"),
            "consequences": item.get("consequences"),
            "recommendations": item.get("recommendations"),
            "treatment": item.get("treatment"),
            "control_keys": item.get("control_keys") or [],
            "frameworks": item.get("frameworks") or [],
            "built_in": True,
        }
        row = existing.pop(item["code"], None)
        if row is None:
            session.add(RiskTemplate(id=uuid7(), code=item["code"], **values))
            result.table("risk_templates").inserted += 1
        elif _apply(row, values):
            result.table("risk_templates").updated += 1
    for stale in existing.values():
        await session.delete(stale)
        result.table("risk_templates").pruned += 1
    await session.flush()


async def _load_capabilities(
    session: AsyncSession, docs: Sequence[dict[str, Any]], result: LoadResult
) -> dict[str, IntegrationCapability]:
    """Upsert capabilities by key. Stale ones are handed back for a late prune."""
    existing = {
        row.key: row for row in (await session.execute(select(IntegrationCapability))).scalars()
    }
    for doc in docs:
        values = {
            "name": doc["name"],
            "description": doc["description"],
            "providers": doc["providers"],
        }
        row = existing.pop(doc["key"], None)
        if row is None:
            session.add(IntegrationCapability(id=uuid7(), key=doc["key"], **values))
            result.table("integration_capabilities").inserted += 1
        elif _apply(row, values):
            result.table("integration_capabilities").updated += 1
    return existing


async def _load_automation(
    session: AsyncSession,
    capabilities: Sequence[dict[str, Any]],
    checks: Sequence[dict[str, Any]],
    result: LoadResult,
) -> None:
    """Upsert capabilities, checks and the check to control template map.

    Checks name templates by code, so this pack loads after the packs that define
    templates (``load_all`` orders it last). A check that has already produced
    results cannot be pruned: ``check_results`` references it without a cascade,
    so the prune fails loudly and history is never orphaned.
    """
    stale_capabilities = await _load_capabilities(session, capabilities, result)
    capability_keys = {doc["key"] for doc in capabilities}
    templates = {
        row.code: row.id for row in (await session.execute(select(ControlTemplate))).scalars()
    }
    existing_checks = {row.key: row for row in (await session.execute(select(Check))).scalars()}
    wanted: dict[tuple[uuid.UUID, uuid.UUID], str] = {}
    for doc in checks:
        unknown = set(doc["capabilities"]) - capability_keys
        missing = [m["code"] for m in doc["controls"] if m["code"] not in templates]
        if unknown or missing:
            raise ValueError(
                f"check {doc['key']}: unknown capabilities {unknown}, controls {missing}"
            )
        values = {
            "name": doc["name"],
            "description": doc["description"],
            "capabilities": doc["capabilities"],
            "implementations": doc["implementations"],
            "resource_type": doc["resource_type"],
            "frequency": doc["frequency"],
            "remediation": doc["remediation"],
        }
        check = existing_checks.pop(doc["key"], None)
        if check is None:
            check = Check(id=uuid7(), key=doc["key"], **values)
            session.add(check)
            result.table("checks").inserted += 1
        elif _apply(check, values):
            result.table("checks").updated += 1
        for mapping in doc["controls"]:
            wanted[(templates[mapping["code"]], check.id)] = mapping["coverage"]
    await session.flush()

    existing_map = {
        (row.template_id, row.check_id): row
        for row in (await session.execute(select(ControlTemplateCheck))).scalars()
    }
    for (template_id, check_id), coverage in wanted.items():
        row = existing_map.pop((template_id, check_id), None)
        if row is None:
            session.add(
                ControlTemplateCheck(
                    id=uuid7(), template_id=template_id, check_id=check_id, coverage=coverage
                )
            )
            result.table("control_template_checks").inserted += 1
        elif _apply(row, {"coverage": coverage}):
            result.table("control_template_checks").updated += 1
    for stale in [*existing_map.values(), *existing_checks.values(), *stale_capabilities.values()]:
        await session.delete(stale)
        result.table(type(stale).__tablename__).pruned += 1
        await session.flush()


async def load_pack(session: AsyncSession, pack: Path) -> LoadResult:
    """Load one content pack directory. Idempotent: a second run changes nothing."""
    result = LoadResult()
    # Packs are not all the same shape: the policy library ships templates and
    # no framework, so each section loads only if its file is present.
    if (pack / "checks.json").exists():
        await _load_automation(
            session, _read(pack, "capabilities.json"), _read(pack, "checks.json"), result
        )
    if (pack / "risk_templates.json").exists():
        await _load_risk_templates(session, _read(pack, "risk_templates.json"), result)
    if (pack / "questionnaire_bank.json").exists():
        await _load_questionnaire_bank(session, _read(pack, "questionnaire_bank.json"), result)
    if (pack / "document_templates.json").exists():
        await _load_document_templates(session, _read(pack, "document_templates.json"), result)
    if not (pack / "framework.json").exists():
        return result
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
            # Checks map to control templates, so a pack that ships checks loads
            # after the packs that define templates.
            ordered = sorted(
                (p for p in CONTENT_ROOT.iterdir() if p.is_dir()),
                key=lambda p: ((p / "checks.json").exists(), p.name),
            )
            for pack in packs or ordered:
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
