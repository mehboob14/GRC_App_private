"""Alembic environment, on the async engine.

Connects with ``DATABASE_MIGRATION_URL`` — the role that owns the schema — rather than
with the application role, which owns nothing and cannot bypass RLS
(docs/architecture/multi-tenancy.md).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from verity.core.config import get_settings
from verity.db.base import Base

# Every module's models must be registered on Base.metadata before autogenerate
# compares it against the database, or autogenerate will confidently propose dropping
# every table it cannot see. Import them here as modules land.
from verity.modules.assets import models as _assets_models  # noqa: F401
from verity.modules.audit import models as _audit_models  # noqa: F401
from verity.modules.compliance import models as _compliance_models  # noqa: F401
from verity.modules.customfields import models as _customfields_models  # noqa: F401
from verity.modules.documents import models as _documents_models  # noqa: F401
from verity.modules.evidence import models as _evidence_models  # noqa: F401
from verity.modules.iam import models as _iam_models  # noqa: F401
from verity.modules.links import models as _links_models  # noqa: F401
from verity.modules.notifications import models as _notifications_models  # noqa: F401
from verity.modules.risk import models as _risk_models  # noqa: F401
from verity.modules.tasks import models as _tasks_models  # noqa: F401
from verity.modules.tenancy import models as _tenancy_models  # noqa: F401
from verity.modules.vendors import models as _vendors_models  # noqa: F401
from verity.modules.vulnerabilities import models as _vulnerabilities_models  # noqa: F401

target_metadata = Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _migration_url() -> str:
    return get_settings().database.effective_migration_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it, for a deploy that is reviewed first."""
    context.configure(
        url=_migration_url(),
        target_metadata=target_metadata,
        # Catch a column whose Python type has drifted from the database's.
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    # NullPool: a migration run is one connection with a long-lived lock, and a pool
    # that outlives the process holds it open after the run has finished.
    engine = create_async_engine(_migration_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
