# Verity — SOC 2 / GRC Compliance Platform

Multi-tenant compliance platform that takes an organisation from "we need SOC 2" to "we are
audit-ready, continuously." Maps Trust Services Criteria to a managed control set, manages the
evidence proving each control, and ties together tasks, documents, risks, vendors, assets, and
vulnerabilities through one connected data model.

## Start here

| If you are | Read |
|---|---|
| An engineer joining | [docs/architecture/overview.md](docs/architecture/overview.md) then [docs/conventions/](docs/conventions/) |
| An AI coding agent | [CLAUDE.md](CLAUDE.md) — binding rules |
| Looking for why | [docs/adr/](docs/adr/) |
| Setting up locally | [docs/runbooks/local-setup.md](docs/runbooks/local-setup.md) |

## Stack

React + TypeScript + Tailwind. Python 3.12 + FastAPI + SQLAlchemy 2.0 async. PostgreSQL 16 with
row-level security. Native auth in Phase 1, behind a seam an external Keycloak-based IdP
federates into later ([ADR-0006](docs/adr/0006-keycloak-as-identity-provider.md)). Redis + Celery
for jobs. S3-compatible object storage for evidence files.

## Run it

```bash
make setup && make up && make migrate
make run          # http://127.0.0.1:8000/healthz
make check test
```

Full walkthrough, including what each database role is for and how to verify the roles are right:
[docs/runbooks/local-setup.md](docs/runbooks/local-setup.md).

## Layout

```
backend/    FastAPI modular monolith, one folder per bounded context
frontend/   React app, features mirror backend modules
docs/       architecture, ADRs, conventions, runbooks
infra/      docker compose, deploy scripts
openspec/   specs and change proposals
```

## How work happens here

Spec-driven. Every change starts as a spec proposal, gets reviewed, then gets implemented against
that spec. Specs are the record of intent; code is the consequence. See
[docs/conventions/workflow.md](docs/conventions/workflow.md).
