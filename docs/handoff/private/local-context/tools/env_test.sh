# Source this before ANY pytest run that touches tests/integration or tests/isolation:
#   cd backend && source ../local-context/tools/env_test.sh
#
# It points at verity_test, the disposable database. Those suites TRUNCATE users and tenants
# CASCADE on whatever DATABASE_URL names, so never source anything that names `verity` (the dev
# database holding real local accounts) or `verity_guide` (the demo workspace).
# Postgres and Redis run inside WSL (cluster `main` on 5433, Redis 6379); see WORKFLOW.md.
export DATABASE_URL="postgresql+asyncpg://verity_app:verity_app@127.0.0.1:5433/verity_test"
export DATABASE_MIGRATION_URL="postgresql+asyncpg://verity_owner:verity_owner@127.0.0.1:5433/verity_test"
export REDIS_URL="redis://127.0.0.1:6379/1"
export ENVIRONMENT="test"
export VERITY_REQUIRE_DB=1
export PYTHONPATH=src
