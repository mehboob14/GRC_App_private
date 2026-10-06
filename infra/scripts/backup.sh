#!/usr/bin/env bash
# Back up the database and the evidence files. Run on the server, from anywhere:
#
#   bash infra/scripts/backup.sh [directory]      # default: ~/verity-backups
#
# The database goes out as a custom format dump (restore with pg_restore), the evidence
# files as a tarball of the evidence-data volume. Both are checked before the script says
# it is done: a dump that cannot be listed is not a backup.
set -euo pipefail

cd "$(dirname "$0")/../.."
DC="docker compose --env-file infra/docker/.env.production -f infra/docker/docker-compose.prod.yml"
OUT="${1:-$HOME/verity-backups}"
STAMP="$(date +%F-%H%M)"
mkdir -p "$OUT"

DUMP="$OUT/verity-$STAMP.dump"
EVIDENCE="$OUT/evidence-$STAMP.tar.gz"

# The user and database names are read inside the container, where .env.production put them.
$DC exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$DUMP"
[ -s "$DUMP" ] || { echo "the database dump is empty: $DUMP" >&2; exit 1; }
$DC exec -T postgres pg_restore --list < "$DUMP" > /dev/null \
  || { echo "the database dump cannot be read back: $DUMP" >&2; exit 1; }

docker run --rm -v verity_evidence-data:/data -v "$OUT":/backup alpine \
  tar czf "/backup/evidence-$STAMP.tar.gz" -C /data .
tar tzf "$EVIDENCE" > /dev/null || { echo "the evidence archive cannot be read back: $EVIDENCE" >&2; exit 1; }

echo "database: $DUMP ($(du -h "$DUMP" | cut -f1))"
echo "evidence: $EVIDENCE ($(du -h "$EVIDENCE" | cut -f1))"
