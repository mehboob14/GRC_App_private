---
name: verity-tests-wipe-database
description: Verity backend integration tests TRUNCATE users/tenants CASCADE; never run them against the dev DB (5433/verity); use verity_test via /tmp/venv_test.sh
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9330b17-d5d7-425a-8820-282896af2e69
  modified: 2026-09-13T19:29:01.342Z
---

Verity's `backend/tests/conftest.py` fixtures `clean_iam` and `clean_tenancy` run `TRUNCATE users ... CASCADE` and `TRUNCATE tenants ... CASCADE` as the owner role on whatever `DATABASE_URL` points at. `/tmp/venv.sh` points at the **dev** database (`127.0.0.1:5433/verity`), so running `pytest tests/integration` after sourcing it wiped every local account and workspace on 2026-09-14 (including the user's own "layeron" test workspace and a portal link they had asked me to fix). No backup existed.

**Why:** the tests assume a disposable test database; the dev shell env silently made the dev DB that database.

**How to apply:** before any `pytest` run that touches `tests/integration` or `tests/isolation`, `source /tmp/venv_test.sh` (points at `verity_test` on the same server, created 2026-09-14, migrated + seeded). Unit tests are safe either way. If `verity_test` is missing: create it as `verity_owner`, grant CONNECT to `verity_app`, `alembic upgrade head`, `python -m verity.manage seed-content`. Related: [[verity-grc-platform]], [[verity-vendors-module]].

**Throwaway container gotcha (2026-09-24):** when the test cluster is created with
`POSTGRES_USER=verity_owner`, that role is a SUPERUSER with BYPASSRLS, so RLS never
applies to it and `tests/integration/test_append_only.py::test_the_owner_role_cannot_update_or_delete_an_audit_row`
fails on an environment difference, not a regression. The WSL cluster on 5433 creates
`verity_owner` as an ordinary role, which is why the test passes there.
