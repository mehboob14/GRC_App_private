
wsl -d Ubuntu -- pg_lsclusters          # expect: 16 main 5433 online

# 2. Backend API on 8001 (from the repo root)
cd backend && ./.venv/Scripts/python.exe -m uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload



wsl -d Ubuntu -- pg_lsclusters


If the cluster shows `down` instead of `online`:

```bash
wsl -d Ubuntu -- sudo pg_ctlcluster 16 main start
wsl -d Ubuntu -- sudo service redis-server start   # if /readyz later reports redis down
```


From the repository root:

```bash
cd backend
PYTHONPATH=src ./.venv/Scripts/python.exe -m uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload
```

PowerShell variant (same thing, PowerShell sets `PYTHONPATH` differently):

```powershell
cd backend
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload
```

If you have `uv` on PATH, this is equivalent and loads `.env` the same way:

```bash
uv --directory backend run uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload
```

Configuration is read from `<repo>/.env` (and `backend/.env` if present, which wins). It is
git-ignored and already has safe local defaults, including the `5433` database URL.

**Confirm it's healthy** (two deliberately different probes):

```bash
curl -s localhost:8001/healthz   # {"status":"ok",...}                — contacts nothing
curl -s localhost:8001/readyz    # {"status":"ready","dependencies":{"database":"ok","redis":"ok"}}
```

If `/readyz` says `database` is down, go back to step 1. API docs are at
`localhost:8001/api/v1/docs` (local/test only).

## Step 3 — web UI (port 5173)

From the repository root:

```bash
cd frontend
npm run dev
```

Vite serves on **http://localhost:5173** and proxies every `/api/...` call to the API on
8001, so the UI talks to the real backend and the real database.

## Step 4 — sign in

There's no seeded demo login; create a workspace once and reuse it.

- **New workspace (self-service signup):** open http://localhost:5173 → *Start a trial*, or
  hit the API directly:

  ```bash
  curl -s -X POST localhost:8001/api/v1/auth/signup -H 'Content-Type: application/json' \
    -d '{"company_name":"Acme","full_name":"Founder","email":"founder@acme.example","password":"orbit-mango-quartz-42"}'
  ```

  The first user holds **Admin**, and Admin requires TOTP, so signup returns
  `mfa_enrollment_required` with a challenge token — enroll via
  `POST /api/v1/auth/mfa/enroll` then `POST /api/v1/auth/mfa/confirm` (see
  [local-setup.md](local-setup.md#sign-up-the-first-workspace) and
  [week1-demo.md](week1-demo.md) for the full flow, including scanning the `otpauth://` URI).

- **Non-admin members** sign in with a password alone after accepting an invite.

## Stopping

- **API / Web:** `Ctrl-C` in their terminals (or stop the background processes).
- **Database / Redis:** they stop when WSL shuts down (`wsl --shutdown`). Leaving WSL
  running between sessions is fine and means the DB is ready next time.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| UI loads but every request fails / spins | API not on 8001 | start step 2 on `--port 8001` |
| API won't start, `ConnectionRefused` on 5433 | WSL/Postgres down | step 1 (`wsl -d Ubuntu -- pg_lsclusters`) |
| `/readyz` → `redis: "down"` | Redis not running in WSL | `wsl -d Ubuntu -- sudo service redis-server start` |
| `verity` import errors on API start | `PYTHONPATH` not set | prefix with `PYTHONPATH=src` (or use `uv run`) |
| Blank page / stale UI after a pull | old Vite cache | delete `frontend/node_modules/.vite`, restart `npm run dev` |
| Port 5173 in use | a previous Vite still running | kill it, or Vite will pick the next free port (update nothing — the proxy is what matters) |

## One-time / occasional

```bash
# Install dependencies (after a fresh clone or a lockfile change)
uv --directory backend sync --frozen --extra dev
cd frontend && npm install

# Apply new database migrations (after pulling schema changes)
cd backend && ./.venv/Scripts/alembic.exe upgrade head

# Load shipped global content (frameworks, control templates, …) — idempotent
cd backend && PYTHONPATH=src ./.venv/Scripts/python.exe -m verity.manage seed-content
```
