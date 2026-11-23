---
name: verity-deploy-runbook
description: "How Verity deploys to the Contabo server: /opt/verity, docker compose prod, migrate BEFORE seed-content"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-08-24T08:53:12.505Z
---

Verity deploys to the shared Contabo box (37.60.228.227) at `/opt/verity`, as
user `mehboob`. Code arrives by `git pull` from `github.com/mehboob14/GRC_App_private`
(branch `main` — work is committed straight to main). Per
[[deploy-and-client-comms-style]] the user runs every server command; hand over a
sheet, never execute.

The compose prefix used for everything:

    docker compose --env-file infra/docker/.env.production -f infra/docker/docker-compose.prod.yml

Sequence (verified working on 2026-08-24):

1. `cd /opt/verity && git pull`
2. `<prefix> up -d --build`
3. `<prefix> run --rm api alembic upgrade head`
4. `<prefix> run --rm api python -m verity.manage seed-content`
5. `<prefix> ps` and a psql verify

**Step 3 must precede step 4.** Seed-content upserts `control_templates` from the
JSON pack. A content migration that decides which tenant rows to refresh by
comparing them to their template would then match nothing, and every tenant would
silently keep the old text. When ordered correctly, seed-content reports
`changed=False` — that is the success signal, not a no-op.

Services: postgres, redis, minio, minio-init, api, web (nginx). Only api/web
rebuild on a normal deploy; postgres/redis/minio keep running for weeks.

`seed-content` only updates the global pack. Nothing re-syncs already-adopted
tenant `controls` — `instantiate_library` is idempotent on
`(tenant_id, template_id)`. Changing shipped control text therefore needs a data
migration; see [[verity-control-content-migration]].

Reading `controls` in psql needs a tenant first, because RLS filters it:
`SELECT set_config('app.current_tenant',(SELECT id::text FROM tenants LIMIT 1),false);`

Related: [[verity-grc-platform]]
