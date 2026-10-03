"""Loading a second framework beside SOC 2 (F17), and refusing content that was not reviewed.

A pack owns what it ships. ISO 27001 maps its requirements onto control templates the
SOC 2 pack ships, adds templates only for what is new, and loading it must leave the
SOC 2 library, its crosswalk and every adopted control exactly as they were. Each test
runs inside a transaction it rolls back, so the shared database is left as found.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from verity.core.config import Settings
from verity.modules.compliance.models import ControlTemplate, Requirement, TemplateRequirementMap
from verity.seed.loader import CONTENT_ROOT, ContentError, load_pack, verify_pack

pytestmark = [pytest.mark.integration]

_NEW_TEMPLATE = {
    "canonical_key": "isms-scope",
    "category": "Governance, Risk & Compliance",
    "sub_category": "Management System",
    "code": "ISM-01",
    "control_sub_type": "Manual",
    "description": "The management system has a stated scope.",
    "implementation_guidance": "State what the management system covers.\nReview it each year.",
    "importance": "mandatory",
    "name": "Management system scope",
    "evidence": [
        {
            "key": "scope-statement",
            "name": "Scope statement",
            "assurance": "design",
            "cadence": "annual",
            "source": "upload",
        }
    ],
}


def _write(pack: Path, name: str, data: object) -> None:
    (pack / name).write_text(json.dumps(data), encoding="utf-8")


def _iso_pack(
    root: Path,
    *,
    with_new_template: bool = True,
    rationale: str = "Why",
    sub_category: str = "Management System",
) -> Path:
    pack = root / "isoprobe"
    pack.mkdir(exist_ok=True)
    _write(
        pack,
        "framework.json",
        {"code": "ISOPROBE", "name": "ISO probe", "version": "2022", "description": "A probe."},
    )
    _write(
        pack,
        "requirements.json",
        [
            {
                "requirement_key": "ISOPROBE:A.8.32",
                "code": "A.8.32",
                "category": "Technological controls",
                "trust_services_category": "Security",
                "name": "Change management",
                "description": None,
                "is_always_in_scope": True,
            }
        ],
    )
    template = {**_NEW_TEMPLATE, "sub_category": sub_category}
    _write(pack, "control_templates.json", [template] if with_new_template else [])
    mappings = [
        {
            "requirement_key": "ISOPROBE:A.8.32",
            "template_code": "SD-06",
            "coverage": "partial",
            "rationale": rationale,
        }
    ]
    if with_new_template:
        mappings.append(
            {
                "requirement_key": "ISOPROBE:A.8.32",
                "template_code": "ISM-01",
                "coverage": "full",
                "rationale": "The scope names what changes are controlled.",
            }
        )
    _write(pack, "template_requirements.json", mappings)
    return pack


@pytest.fixture
async def owner(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(settings.database.effective_migration_url)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session, session.begin():
            yield session
            await session.rollback()
    finally:
        await engine.dispose()


async def _counts(session: AsyncSession) -> tuple[int, int, int]:
    async def count(model: type) -> int:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)

    soc2 = await session.scalar(
        select(func.count()).select_from(ControlTemplate).where(ControlTemplate.pack == "soc2")
    )
    return int(soc2 or 0), await count(TemplateRequirementMap), await count(Requirement)


async def test_a_second_framework_loads_beside_soc2_without_touching_it(
    owner: AsyncSession, tmp_path: Path
) -> None:
    soc2_templates, mappings, requirements = await _counts(owner)
    assert soc2_templates > 100

    pack = _iso_pack(tmp_path)
    first = await load_pack(owner, pack)
    assert first.table("control_templates").inserted == 1
    assert first.table("template_requirement_map").inserted == 2
    assert first.table("control_templates").pruned == 0
    assert first.table("template_requirement_map").pruned == 0

    after_soc2, after_mappings, after_requirements = await _counts(owner)
    assert after_soc2 == soc2_templates  # SOC 2's own templates are untouched
    assert after_mappings == mappings + 2
    assert after_requirements == requirements + 1

    # The mapping from the new framework points at a template SOC 2 ships, and the
    # template the new pack ships is owned by it.
    owned = await owner.scalar(select(ControlTemplate.pack).where(ControlTemplate.code == "ISM-01"))
    assert owned == "isoprobe"
    assert (
        await owner.scalar(select(ControlTemplate.pack).where(ControlTemplate.code == "SD-06"))
        == "soc2"
    )

    # Loading it again changes nothing.
    again = await load_pack(owner, pack)
    assert not again.changed


async def test_dropping_a_template_from_one_pack_prunes_only_that_pack(
    owner: AsyncSession, tmp_path: Path
) -> None:
    soc2_templates, mappings, _ = await _counts(owner)
    await load_pack(owner, _iso_pack(tmp_path))
    smaller = await load_pack(owner, _iso_pack(tmp_path, with_new_template=False))
    assert smaller.table("control_templates").pruned == 1
    assert smaller.table("template_requirement_map").pruned == 1
    after_soc2, after_mappings, _ = await _counts(owner)
    assert after_soc2 == soc2_templates
    assert after_mappings == mappings + 1  # the mapping onto SD-06 remains


async def test_a_reviewed_rationale_reaches_a_mapping_already_loaded(
    owner: AsyncSession, tmp_path: Path
) -> None:
    await load_pack(owner, _iso_pack(tmp_path, rationale="First reading."))
    updated = await load_pack(owner, _iso_pack(tmp_path, rationale="Reviewed reading."))
    assert updated.table("template_requirement_map").updated == 1
    stored = await owner.scalar(
        select(TemplateRequirementMap.rationale)
        .join(ControlTemplate, ControlTemplate.id == TemplateRequirementMap.template_id)
        .where(
            ControlTemplate.code == "SD-06", TemplateRequirementMap.rationale == "Reviewed reading."
        )
    )
    assert stored == "Reviewed reading."


async def test_the_sub_type_is_written_with_a_template_and_refreshed_on_one_already_loaded(
    owner: AsyncSession, tmp_path: Path
) -> None:
    await load_pack(owner, _iso_pack(tmp_path))
    stored = select(ControlTemplate.sub_category).where(ControlTemplate.code == "ISM-01")
    assert await owner.scalar(stored) == "Management System"

    refreshed = await load_pack(owner, _iso_pack(tmp_path, sub_category="Scope and Context"))
    assert refreshed.table("control_templates").updated == 1
    assert await owner.scalar(stored) == "Scope and Context"
    unchanged = await load_pack(owner, _iso_pack(tmp_path, sub_category="Scope and Context"))
    assert not unchanged.changed


async def test_the_shipped_pack_restores_a_sub_type_a_template_lost(owner: AsyncSession) -> None:
    """The loader refreshes the Sub-type of a SOC 2 template already in the table."""
    code = "IAM-04"
    stored = select(ControlTemplate.sub_category).where(ControlTemplate.code == code)
    shipped = await owner.scalar(stored)
    assert shipped, "seed-content has not written the Sub-types"
    await owner.execute(
        update(ControlTemplate).where(ControlTemplate.code == code).values(sub_category=None)
    )

    result = await load_pack(owner, CONTENT_ROOT / "soc2")
    assert result.table("control_templates").updated >= 1
    assert await owner.scalar(stored) == shipped


async def test_a_mapping_nobody_explained_is_refused(owner: AsyncSession, tmp_path: Path) -> None:
    pack = _iso_pack(tmp_path, rationale="   ")
    with pytest.raises(ContentError, match="rationale"):
        await load_pack(owner, pack)


def test_a_pack_that_differs_from_its_sealed_hashes_is_refused(tmp_path: Path) -> None:
    pack = _iso_pack(tmp_path)
    verify_pack(pack)  # no manifest, nothing sealed
    _write(
        pack,
        "MANIFEST.json",
        {"generated": [{"path": "requirements.json", "sha256": "0" * 64}]},
    )
    with pytest.raises(ContentError, match=r"requirements\.json"):
        verify_pack(pack)
