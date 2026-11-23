"""A demo workspace on SOC 2 with some controls worked, and a session file for shot_demo.py.

Run from backend/ with env_demo.sh sourced, SMTP_HOST= and LEADS_NOTIFY_EMAIL= set empty, the demo
API (run_demo_api.py) up on 8111, and PYTHONPATH="src;." so tests.support resolves:

    cd backend && source ../local-context/tools/env_demo.sh
    SMTP_HOST= LEADS_NOTIFY_EMAIL= PYTHONPATH="src;." .venv/Scripts/python.exe ../local-context/tools/demo_seed.py

Signs up "Northwind Software Ltd", sets a SOC 2 Type II engagement, marks 40 controls implemented and
writes demo_session.json next to this file (a bearer token for the demo database only).
Add ISO 27001 afterwards through the UI (Frameworks, Add to workspace) to see the multi-framework screens.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from tests.support.iam import signup_workspace, tenant_session_headers
from verity.core.db import dispose_engine

BASE = "http://127.0.0.1:8111/api/v1"
OUT = Path(__file__).with_name("demo_session.json")


async def main() -> None:
    ws = await signup_workspace(company="Northwind Software Ltd", email="demo-iso@northwind.example")
    headers = tenant_session_headers(ws.membership_id)
    async with httpx.AsyncClient(base_url=BASE, headers=headers, timeout=120) as api:
        me = (await api.get("/auth/me")).json()
        frameworks = (await api.get("/tenant-frameworks")).json()
        soc2 = next(f for f in frameworks if f["code"] == "SOC2")
        put = await api.put(
            "/engagement",
            json={
                "name": "SOC 2 Type II 2026",
                "framework_version_id": soc2["version_id"],
                "audit_type": "type_2",
                "categories_in_scope": ["Availability", "Confidentiality"],
                "window_start": "2026-01-01",
                "window_end": "2026-12-31",
                "status": "active",
            },
        )
        print("engagement", put.status_code)
        controls = (await api.get("/controls")).json()
        worked = 0
        for control in controls:
            if control["code"].startswith(("GOV-", "IAM-", "SD-", "HR-")) and worked < 40:
                r = await api.patch(f"/controls/{control['id']}", json={"status": "implemented"})
                worked += r.status_code == 200
        print("implemented", worked)
    OUT.write_text(json.dumps({"token": headers["Authorization"][7:], "principal": me}), encoding="utf-8")
    await dispose_engine()
    print("seeded", ws.tenant_id)


asyncio.run(main())
