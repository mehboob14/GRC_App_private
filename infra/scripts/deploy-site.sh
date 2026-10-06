#!/usr/bin/env bash
# Build and (re)start the public website. Run on the server from the checkout of the website
# branch, which is a separate worktree from the platform's (docs/runbooks/website.md):
#
#   cd /opt/verity-site
#   bash infra/scripts/deploy-site.sh
#
# The site is its own compose project: no database, nothing to migrate, nothing to back up.
# A deploy builds the static files into a new image and swaps one nginx container. The
# platform's containers are not touched.
set -euo pipefail

cd "$(dirname "$0")/../.."
ENV_FILE=infra/docker/.env.website
DC="docker compose --env-file $ENV_FILE -f infra/docker/docker-compose.website.yml"
EDGE_NGINX="${EDGE_NGINX:-keycloak-nginx}"
NETWORK=verity-site_default

say() { printf '\n== %s\n' "$*"; }

[ -f "$ENV_FILE" ] || { echo "$ENV_FILE is missing: cp infra/docker/.env.website.example $ENV_FILE" >&2; exit 1; }
SITE_URL="$(grep -E '^SITE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
[ -n "$SITE_URL" ] || { echo "SITE_URL is empty in $ENV_FILE" >&2; exit 1; }

say "What will go out"
git log -1 --format='commit:  %h %s (%an, %ad)' --date=short
echo "address: $SITE_URL"

say "Build and start"
$DC up -d --build

say "Checks"
state=""
for _ in $(seq 1 12); do
  state="$(docker inspect -f '{{.State.Health.Status}}' verity-site 2>/dev/null || true)"
  [ "$state" = "healthy" ] && break
  sleep 5
done
echo "verity-site: ${state:-unknown}"
[ "$state" = "healthy" ] || { echo "not healthy. Read why with: $DC logs --tail 40 site" >&2; exit 1; }

# The address is baked in at build time. If robots.txt does not name it, the env file was
# wrong or the image is an old one.
robots="$(docker exec verity-site wget -qO- http://127.0.0.1/robots.txt)"
case "$robots" in
  *"$SITE_URL/sitemap.xml"*) echo "address in the build: $SITE_URL" ;;
  *) echo "robots.txt does not name $SITE_URL, so the image was built with another address" >&2; exit 1 ;;
esac

say "Edge proxy"
if ! docker inspect "$EDGE_NGINX" >/dev/null 2>&1; then
  echo "No container named $EDGE_NGINX here. Name yours with EDGE_NGINX=<name>, or run:"
  echo "  docker network connect $NETWORK <name>"
else
  nets="$(docker inspect -f '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}' "$EDGE_NGINX")"
  case " $nets" in
    *" $NETWORK "*) echo "$EDGE_NGINX can already reach verity-site" ;;
    *) docker network connect "$NETWORK" "$EDGE_NGINX" \
         && echo "connected $EDGE_NGINX to $NETWORK" \
         || echo "could not connect $EDGE_NGINX: docker network connect $NETWORK <its name>" ;;
  esac
fi
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$SITE_URL/" || true)"
echo "public: $SITE_URL/ answered ${code:-nothing} (200 once the edge block and certificate are in place)"

say "Done"
echo "To go back: git checkout --detach <the earlier commit>, then bash infra/scripts/deploy-site.sh"
echo "To take the site down: $DC down (the platform is not affected)"
