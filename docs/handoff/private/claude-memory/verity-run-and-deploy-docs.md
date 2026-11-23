---
name: verity-run-and-deploy-docs
description: "Where the run-the-app and deployment runbooks live, and the exact local start sequence for the Verity platform"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-29T11:55:29.066Z
---

Two runbooks in C:\Development\Verity_GRC_Platform (written 2026-08-25, authoritative — prefer them over guessing):
- **docs/runbooks/running-the-app.md** — run the full stack locally on this Windows+WSL box.
- **docs/runbooks/deployment.md** — the production Docker Compose deploy (`/opt/verity`, edge nginx + TLS, backups, ops, rollback).

**Local start sequence (this machine):** Postgres 16 + Redis run NATIVE inside WSL Ubuntu (pg cluster `main` on **5433**, not docker) and auto-start when WSL starts — so if the DB is refusing connections, WSL is just stopped (`wsl -d Ubuntu -- pg_lsclusters` → expect `online`). Backend API runs on Windows on **8001** (8000 is occupied; vite.config proxies /api → 127.0.0.1:8001): `cd backend && PYTHONPATH=src ./.venv/Scripts/python.exe -m uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload`. Frontend: `cd frontend && npm run dev` (vite 5173). No seeded demo login — sign up a workspace (Admin → forced TOTP enrollment). See [[verity-preview-browser-login]] for the token-inject shortcut when driving the preview browser headless.

Deploy essentials: single-host `infra/docker/docker-compose.prod.yml` (postgres/redis/minio/api/web/worker/beat), app connects as `verity_app` (NOBYPASSRLS), migrations as `verity_owner`. Ordered deploy: `git pull` → `dc build` → `dc up -d` → `alembic upgrade head` → `manage seed-content` (migrate ALWAYS, before seed). Manage cmds: `seed-platform-admin`, `seed-content`.
