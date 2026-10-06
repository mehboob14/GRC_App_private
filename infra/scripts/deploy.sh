#!/usr/bin/env bash
# Deploy the checked-out revision of Verity. Run on the server, inside tmux (the frontend
# build takes minutes and an SSH drop would kill it):
#
#   cd /opt/verity
#   tmux new -s deploy
#   git fetch origin && git checkout <branch> && git pull
#   bash infra/scripts/deploy.sh          # add -y to skip the question
#
# In order: show what will go out, back up, build, migrate, swap the containers, load the
# shipped content, then check that the API is ready and that the worker and the scheduler
# stay up. Migrations run before the swap on purpose: every migration so far only adds, so
# the old code is fine on the new schema and the new code never meets the old one. Nothing
# here deletes data.
set -euo pipefail

cd "$(dirname "$0")/../.."
DC="docker compose --env-file infra/docker/.env.production -f infra/docker/docker-compose.prod.yml"

say() { printf '\n== %s\n' "$*"; }
revision() { grep -E '^[0-9a-f]{12}' | head -1 | awk '{print $1}'; }

[ -f infra/docker/.env.production ] || { echo "infra/docker/.env.production is missing" >&2; exit 1; }

say "What will go out"
echo "branch:  $(git rev-parse --abbrev-ref HEAD)"
git log -1 --format='commit:  %h %s (%an, %ad)' --date=short
if [ -n "$(git status --porcelain)" ]; then
  echo "warning: the server checkout has local changes:"
  git status --short
fi
BEFORE="$($DC run --rm -T api alembic current 2>&1 | revision || true)"
echo "database is at migration: ${BEFORE:-unknown}"

if [ "${1:-}" != "-y" ]; then
  read -r -p "Deploy this revision? [y/N] " answer
  [ "$answer" = "y" ] || { echo "Stopped. Nothing was changed."; exit 1; }
fi

say "Backups"
bash infra/scripts/backup.sh

say "Build"
$DC build

say "Migrate"
$DC run --rm -T api alembic upgrade head

say "Swap the containers"
$DC up -d

# nginx looks up the names it proxies to once, when it loads its config. After the swap each
# proxy in front of the stack still holds the old container addresses and answers 502 until it
# reloads. A reload is graceful (no connection is dropped), and a failure here only warns: the
# deploy itself is done, and the fallback is the restart named in the message.
say "Proxies"
reload_nginx() {
  if ! docker inspect "$1" >/dev/null 2>&1; then
    echo "no container named $1: reload that proxy yourself if you run one"
  elif docker exec "$1" nginx -t >/dev/null 2>&1 && docker exec "$1" nginx -s reload >/dev/null 2>&1; then
    echo "reloaded $1"
  else
    echo "could not reload $1: run  docker restart $1" >&2
  fi
}
reload_nginx verity-web
reload_nginx "${EDGE_NGINX:-keycloak-nginx}"

say "Shipped content and existing workspaces"
$DC run --rm -T api python -m verity.manage seed-content
$DC run --rm -T api python -m scripts.backfill_adopt_soc2

say "Checks"
$DC ps
CURRENT="$($DC run --rm -T api alembic current 2>&1 | revision || true)"
HEAD="$($DC run --rm -T api alembic heads 2>&1 | revision || true)"
if [ -n "$HEAD" ] && [ "$CURRENT" = "$HEAD" ]; then
  echo "migrations: at head ($HEAD)"
else
  echo "migrations: at '${CURRENT}', head is '${HEAD}'" >&2
  exit 1
fi

ready=""
for _ in $(seq 1 12); do
  if ready="$($DC exec -T api python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/readyz').read().decode())" 2>/dev/null)"; then
    break
  fi
  ready=""
  sleep 5
done
[ -n "$ready" ] || { echo "the API did not become ready within a minute: dc logs api" >&2; exit 1; }
echo "readyz: $ready"

# The worker runs every job and beat is what schedules them. A container that restarts
# or has exited means nothing scheduled will run, however healthy the API looks.
sleep 15
down=""
for name in verity-worker verity-beat; do
  state="$(docker inspect -f '{{.State.Status}} restarts={{.RestartCount}}' "$name" 2>&1 || true)"
  echo "$name: $state"
  [ "$state" = "running restarts=0" ] || down="$down $name"
done
if [ -n "$down" ]; then
  echo "not staying up:$down. Read why with: $DC logs --tail 40$down" >&2
  exit 1
fi
$DC logs --tail 15 worker beat

# What a visitor reaches: the public address, through every proxy on the way. Informational,
# because the host may not be able to reach its own public address.
PUBLIC="$(grep -E '^FRONTEND_BASE_URL=' infra/docker/.env.production | head -1 | cut -d= -f2- | tr -d "\"'")"
if [ -n "$PUBLIC" ]; then
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "${PUBLIC%/}/api/v1/openapi.json" || true)"
  echo "public: ${PUBLIC%/}/api/v1/openapi.json answered ${code:-nothing} (200 when the proxies reach the API)"
fi

say "Done"
echo "Was at migration ${BEFORE:-unknown}. To go back: git checkout <the earlier commit>, then"
echo "  $DC build && $DC up -d"
echo "(No migration needs undoing: they only add. The backups are in ~/verity-backups.)"
