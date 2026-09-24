"""check_results is partitioned by month (ER 5.9). The migration pre-creates the
months; this fails six months before they run out, so the follow up migration is
written long before rows start landing in the default partition."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

_MIGRATION = (
    Path(__file__).parents[2]
    / "src/verity/db/migrations/versions/20260919_1000_connectors_github.py"
)


def test_monthly_partitions_cover_at_least_the_next_six_months() -> None:
    spec = importlib.util.spec_from_file_location("connectors_migration", _MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    year, month = module.LAST_PARTITION
    now = datetime.now(UTC)
    months_left = (year - now.year) * 12 + (month - now.month)
    assert months_left >= 6, "extend check_results partitions with a new migration"
