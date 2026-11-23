"""The API against the isolated demo database (verity_guide on the WSL cluster, 5433).

  cd backend && .venv/Scripts/python.exe ../local-context/tools/run_demo_api.py

Serves on 8111, because 8001 (the usual API port) and 8000 belong to other projects on this machine.
There is no auto reload on this Windows setup: restart this process after every backend change,
or it silently serves stale code. Pair it with the vite config next to it (port 5175, proxy to 8111):

  cd frontend && npx vite --config ../local-context/tools/vite.demo.config.mjs

CONNECTORS_GITHUB_API_URL points at a fake GitHub on 8766 (not included here; only needed to demo
connector runs, and nothing else breaks without it).
"""

import os
import sys

os.environ.update(
    {
        "DATABASE_URL": "postgresql+asyncpg://verity_app:verity_app@127.0.0.1:5433/verity_guide",
        "DATABASE_MIGRATION_URL": "postgresql+asyncpg://verity_owner:verity_owner@127.0.0.1:5433/verity_guide",
        "REDIS_URL": "redis://127.0.0.1:6379/3",
        "ENVIRONMENT": "development",
        "CONNECTORS_GITHUB_API_URL": "http://127.0.0.1:8766",
        # The repository-root .env carries real SMTP credentials. Empty values win over the
        # file, so this demo can never send mail.
        "SMTP_HOST": "",
        "LEADS_NOTIFY_EMAIL": "",
    }
)
os.chdir("C:/Development/Verity_GRC_Platform/backend")
sys.path.insert(0, "C:/Development/Verity_GRC_Platform/backend/src")

import uvicorn  # noqa: E402

uvicorn.run("verity.main:app", host="127.0.0.1", port=8111)
