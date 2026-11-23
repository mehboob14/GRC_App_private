# The isolated demo database (verity_guide on the WSL cluster, port 5433). Never the dev database `verity`.
#   cd backend && source ../local-context/tools/env_demo.sh
# Used for screenshots and UI checks, with run_demo_api.py (API on 8111) and vite.demo.config.mjs (5175).
# Anything that signs up or sends mail must also run with SMTP_HOST= and LEADS_NOTIFY_EMAIL= set to
# empty strings: the repo-root .env holds real SMTP credentials and would really send.
export DATABASE_URL="postgresql+asyncpg://verity_app:verity_app@127.0.0.1:5433/verity_guide"
export DATABASE_MIGRATION_URL="postgresql+asyncpg://verity_owner:verity_owner@127.0.0.1:5433/verity_guide"
export REDIS_URL="redis://127.0.0.1:6379/3"
export ENVIRONMENT="development"
export PYTHONPATH=src
