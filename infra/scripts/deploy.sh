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
# shipped content, check. Migrations run before the swap on purpose: every migration so far
# only adds, so the old code is fine on the new schema and the new code never meets the old
# one. Nothing here deletes data.
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

$DC logs --tail 15 worker beat

say "Done"
echo "Was at migration ${BEFORE:-unknown}. To go back: git checkout <the earlier commit>, then"
echo "  $DC build && $DC up -d"
echo "(No migration needs undoing: they only add. The backups are in ~/verity-backups.)"
