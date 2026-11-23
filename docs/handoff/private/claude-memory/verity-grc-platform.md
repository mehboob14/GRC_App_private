---
name: verity-grc-platform
description: "Verity_GRC_Platform Week 1 build state, run commands, and HP-machine environment quirks"
metadata: 
  node_type: memory
  type: project
  originSessionId: 70afa149-15c7-47ca-91dd-848cdb9d5ba4
  modified: 2026-08-13T11:44:59.725Z
---

`C:\Development\Verity_GRC_Platform` is the from-scratch multi-tenant SOC 2/GRC platform (separate from grc-s). Week 1 is built, tested, committed on `main` (git initialised this session): backend `audit` + `tenancy` (provider plane) + `iam` modules (native auth, TOTP MFA, RBAC, `tenant_memberships`, invitations with a time-boxed guest-auditor path), three Alembic migrations, full RLS + isolation tests; frontend is the Design System v1.0 (light/dark tokens, DS components, all Week 1 screens). Backend suite: 429 passing. Identity is native-auth-now behind an IdP seam; external Keycloak federates later (see [[verity-design-reskin]] for the broader design-system context).

**HP-machine run quirks (all confirmed this session):**
- Postgres 16 + Redis run inside **WSL** on `localhost:5433` / `localhost:6379` (NOT Docker — unavailable; NOT the Windows-native PG17 on 5432, whose creds differ). WSL idle-terminates and kills the port forwards — keep a `wsl -e sleep infinity` process alive while running the stack.
- API runs on **port 8001** (8000 is a separate audio-to-text app — do not kill).
- Tests need env overrides (conftest defaults to 5432): `DATABASE_URL=postgresql+asyncpg://verity_app:verity_app@localhost:5433/verity DATABASE_MIGRATION_URL=...verity_owner...5433... REDIS_URL=redis://localhost:6379/1 VERITY_REQUIRE_DB=1 uv --directory backend run pytest`. `.env` is already repointed to 5433.
- `make` is NOT installed (Windows or WSL) — run the raw commands from the Makefile.
- **Frontend browser preview runs against MSW mocks, not the real API**: the host process env has `VITE_USE_MOCKS=true`, and Vite's dotenv won't override an already-set process var, so `.env.local=false` does not win. The code correctly defaults mocks OFF; this is an environment override only. Real-backend proof comes from `backend/scripts/week1_demo.py` (runnable E2E: two orgs, admin MFA, guest auditor in both, switch, audit trail) + the suite. Mock demo admin: `alex.okafor@northwind.cloud` / `Password123!`, MFA code `123456` (alex is in two orgs → exercises the workspace picker).

**Signup is verify-first (added after Week 1 core):** self-service signup now requires a Terms checkbox and mails a real email-verification link (SMTP configured in `.env` — Gmail app password for `aliyanulhaq309@gmail.com`; `core/email.py` mailer via aiosmtplib, no-op when `SMTP_HOST` empty, forced off in tests). Flow: signup → `email_verification_required` (email sent) → `POST /auth/verify-email {token}` → `mfa_enrollment_required` → QR-code MFA enroll → session. Invited users are auto-verified by accepting. `users.email_verified_at` + `terms_accepted_at` columns added; `email_verify` token type. 429 backend tests green. Real email delivery confirmed working.

Restart the API (kill the process on 8001, relaunch `uvicorn verity.main:app --port 8001`) after any backend change — `--reload` is unreliable on this Windows setup and silently serves stale code. Signup is now no-forced-MFA: MFA is off by default and admin-toggled per tenant (`tenant_settings.require_admin_mfa`, GET/PATCH `/tenant/security`, `security:manage` perm); consumer email domains (gmail etc.) are blocked on signup. Running the test suite truncates the shared `verity` DB, wiping app data — don't run tests while the user is testing.

The Week 1 adversarial-review findings and their disposition are in `openspec/changes/week1-review-findings.md`; open spec decisions in `week1-review-decisions.md`.
