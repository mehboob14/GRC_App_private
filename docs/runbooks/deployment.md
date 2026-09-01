# Deployment

How Verity is deployed: a single-host **Docker Compose** stack behind an edge reverse proxy
that terminates TLS. This is the production topology for Phase 1 — one box, self-contained,
publishing nothing to the outside except through the proxy.

The stack file is [`infra/docker/docker-compose.prod.yml`](../../infra/docker/docker-compose.prod.yml).
It is a **separate** file from the dev `docker-compose.yml`, not an override: the dev file
publishes every port to the host for native processes to reach; the prod file publishes
**nothing at all**, so it cannot collide with or be reached through anything else on the box.

> Convention on this project: the server lives at `/opt/verity`, and every command below is
> run from there. A short alias keeps the compose invocation readable:
>
> ```bash
> cd /opt/verity
> alias dc='docker compose --env-file infra/docker/.env.production -f infra/docker/docker-compose.prod.yml'
> ```

## Architecture

| Service | Image | Role | Published? |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | database; init script creates the three roles | no |
| `redis` | `redis:7-alpine` | broker for Celery, cache | no |
| `minio` | `minio/minio` (pinned) | S3-compatible object store for evidence | no |
| `minio-init` | `minio/mc` | one-shot: creates the evidence bucket, enables versioning | — |
| `api` | `verity-api` (built) | FastAPI app (uvicorn) | no — proxied |
| `web` | `verity-web` (built) | the built React app on nginx, fixed name `verity-web` | no — proxied |
| `worker` | `verity-api` | Celery worker (SLA sweep, email outbox) | no |
| `beat` | `verity-api` | Celery scheduler — exactly one instance | no |

Everything sits on the compose network (`verity_default`). The **edge proxy** (the host's own
nginx) joins that network and `proxy_pass`es to `verity-web`; `verity-web`'s nginx serves the
static app and reverse-proxies `/api` to `api`. Nothing binds a host port, so the only way in
is the proxy.

### The database role split (why it matters)

The Postgres init script ([`infra/docker/postgres/init/01-roles.sh`](../../infra/docker/postgres/init/01-roles.sh))
creates three roles on first boot:

| Role | Used by | Properties |
|---|---|---|
| `verity_owner` | migrations only | owns the schema |
| `verity_app` | the API and the workers | owns nothing, `NOSUPERUSER`, `NOBYPASSRLS` |
| `verity_readonly` | ad-hoc reads | `SELECT` only; RLS still applies |

The app connects as `verity_app`, which **cannot bypass row-level security** — the wall that
keeps one tenant out of another's data. Migrations connect as `verity_owner` via
`DATABASE_MIGRATION_URL`. Never point the app at the owner.

## Prerequisites

- A Linux host with **Docker Engine + Compose v2**.
- DNS: an `A`/`AAAA` record for your domain → the host.
- The edge nginx (or Caddy/Traefik) and `certbot` on the host, for TLS.
- A completed **`infra/docker/.env.production`** (next section). It is git-ignored and never
  committed.

## The environment file

Copy the example and fill in real values:

```bash
cp infra/docker/.env.production.example infra/docker/.env.production
# then edit it — every value below must be set
```

| Key(s) | Notes |
|---|---|
| `ENV=production` | turns on the guards below |
| `SECRET_KEY`, `APP_ENCRYPTION_KEY` | generate fresh; **the app refuses to start in production with the dev defaults** |
| `DATABASE_OWNER_USER/PASSWORD`, `DATABASE_APP_USER/PASSWORD`, `DATABASE_READONLY_USER/PASSWORD`, `DATABASE_NAME` | consumed by the Postgres init script |
| `DATABASE_URL` | the **app** URL → `verity_app` |
| `DATABASE_MIGRATION_URL` | the **migration** URL → `verity_owner` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `STORAGE_DRIVER`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_USE_PATH_STYLE` | evidence object store (MinIO here) |
| `FRONTEND_BASE_URL` | your public URL, e.g. `https://app.example.com` — used in email links |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM_EMAIL` | outbound email (notifications, verification, invites) |

The `:?` guards in the compose file mean a missing required secret **fails the command with a
named error** rather than silently starting a mis-configured stack.

## First deployment

```bash
# 0. On the server
sudo mkdir -p /opt/verity && cd /opt/verity
git clone <repo-url> .          # or: git clone <repo-url> /opt/verity

# 1. Configure
cp infra/docker/.env.production.example infra/docker/.env.production
$EDITOR infra/docker/.env.production        # fill in every value

# 2. Build the images and bring the stack up (postgres init runs on first boot)
dc up -d --build

# 3. Wait for postgres to be healthy, then migrate (as the owner role)
dc run --rm api alembic upgrade head

# 4. Seed the shipped global content (frameworks, control templates, checks) — idempotent
dc run --rm api python -m verity.manage seed-content

# 5. Seed the first platform admin (prints a one-time password, once)
dc run --rm api python -m verity.manage seed-platform-admin \
    --email ops@example.com --name "Ops Admin" --role super_admin
```

**Order is not optional:** migrate **before** seed-content — seeding writes rows the migration
created, and content seeding under `FORCE` RLS reads nothing until the schema exists. The first
platform admin is created unenrolled; TOTP enrollment is forced on first login (the provider
plane requires MFA — see [local-setup.md](local-setup.md#seed-the-first-platform-admin)).

Then wire the edge proxy (below) and browse to `FRONTEND_BASE_URL`.

## Edge proxy + TLS

`verity-web` has a fixed container name so the proxy target survives rebuilds. Join the host's
nginx to the compose network and proxy to it:

```bash
docker network connect verity_default <your-host-nginx-container>   # once
```

Minimal nginx server block (the host nginx, terminating TLS):

```nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate     /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;

    location / {
        proxy_pass http://verity-web;            # resolves on the compose network
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
server {                                          # redirect 80 → 443
    listen 80;
    server_name app.example.com;
    return 301 https://$host$request_uri;
}
```

Certificates via Let's Encrypt:

```bash
sudo certbot --nginx -d app.example.com          # issues + installs, sets up auto-renewal
sudo certbot renew --dry-run                      # confirm renewal works
```

`verity-web`'s own nginx already reverse-proxies `/api` to the `api` service, so the host proxy
only needs the single `location /` block above. The API's `/readyz` (reachable as
`http://verity-web/api/v1/... ` internally, or `dc exec api curl localhost:8000/readyz`)
reports each dependency and answers 503 when one is down.

## Routine deployment (updating)

```bash
cd /opt/verity
git pull                                   # fetch the new revision

dc build                                   # rebuild api + web images
dc up -d                                   # recreate changed containers
dc run --rm api alembic upgrade head       # apply any new migrations — ALWAYS
dc run --rm api python -m verity.manage seed-content   # pick up new shipped content
```

- **Always run `alembic upgrade head` after a pull**, even when you don't think the schema
  changed — it is a no-op when there's nothing to apply, and forgetting it is the usual cause
  of a post-deploy 500.
- `worker` and `beat` run on by default; a code change reaches them on the next `dc up -d`
  because they share the `verity-api` image.
- Zero-downtime is not a Phase-1 goal; `dc up -d` recreates in place with a brief blip.

## Backup and restore

Two things hold state: the Postgres volume and the MinIO (evidence) volume.

```bash
# Backup the database (custom format, compressed)
dc exec -T postgres pg_dump -U "$DATABASE_OWNER_USER" -Fc "$DATABASE_NAME" > verity-$(date +%F).dump

# Backup evidence objects (MinIO data volume) — snapshot the named volume
docker run --rm -v verity_minio-data:/data -v "$PWD":/backup alpine \
    tar czf /backup/minio-$(date +%F).tar.gz -C /data .
```

```bash
# Restore the database into a fresh, empty DB (roles must already exist)
dc exec -T postgres pg_restore -U "$DATABASE_OWNER_USER" -d "$DATABASE_NAME" --clean --if-exists < verity-YYYY-MM-DD.dump

# Restore evidence objects
docker run --rm -v verity_minio-data:/data -v "$PWD":/backup alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/minio-YYYY-MM-DD.tar.gz -C /data"
```

Test a restore into a throwaway stack before you need it — an untested backup is a guess.
(Demonstrated backup + restore is a Phase-1 exit criterion.)

## Operations

```bash
dc ps                                  # what's running
dc logs -f api                         # follow the API log (structured JSON, secrets redacted)
dc logs -f worker beat                 # the schedulers
dc restart api                         # restart one service
dc exec api python -m verity.manage seed-content   # re-run a management command
dc down                                # stop the stack, keep the data
dc down -v                             # stop AND delete all data — destructive
```

- **Logs** are structured and run through the redaction pipeline — connector credentials and
  anything password-shaped never reach them.
- **Health:** `dc exec api curl -s localhost:8000/readyz` → `database`, `redis` each report
  `ok`/`down`; the process answers 503 (not death) when a dependency is down, so an unready
  replica leaves the load balancer and keeps running.

## Rollback

```bash
git checkout <previous-tag-or-sha>
dc build && dc up -d
# If the bad release ran a migration, reverse it explicitly (every migration has a downgrade):
dc run --rm api alembic downgrade -1
```

Roll the schema back only when the new migration is the problem; most rollbacks are code-only
and need no `downgrade`.

## Security posture (what's deliberate)

- **No host ports published** by the prod stack — the proxy is the only ingress.
- **App runs as `verity_app`**, which cannot bypass RLS; migrations run as the owner.
- **The API image runs as a non-root user** (uid 1001; `make build-check` asserts it).
- **The web image ships with the mock service worker stripped** (`make build-check` asserts
  `mockServiceWorker.js` is absent) — production never serves mocks.
- **Secrets live only in `infra/docker/.env.production`** on the host, never in git; the
  production config validators refuse to start with the development `SECRET_KEY` /
  `APP_ENCRYPTION_KEY`.
