#!/usr/bin/env bash
# Put the public website on the shared edge nginx: a certificate for its hostname and one
# server block. Run as root by whoever owns the edge, whose config lives under /root and is
# mounted read-only into the container:
#
#   sudo bash /home/mehboob/verity-site/infra/scripts/edge-add-website.sh [hostname]
#
# The default hostname is the temporary sslip.io one. Nothing else is changed. The new block
# is tested with `nginx -t` before the reload and removed again if nginx rejects it, so a bad
# run leaves the edge as it was. Run it again with another hostname once a DNS record exists.
set -euo pipefail

HOST="${1:-website.37-60-228-227.sslip.io}"
EDGE="${EDGE_NGINX:-keycloak-nginx}"
PLATFORM_HOST="${PLATFORM_HOST:-runwaydream.com}"
TEMPLATE="$(dirname "$0")/../docker/edge-nginx-website.conf.template"

say() { printf '\n== %s\n' "$*"; }
die() { echo "$*" >&2; exit 1; }
mount_source() { docker inspect -f "{{range .Mounts}}{{if eq .Destination \"$1\"}}{{.Source}}{{end}}{{end}}" "$EDGE"; }

[ "$(id -u)" = 0 ] || die "Run as root: sudo bash $0 [hostname]"
docker inspect "$EDGE" >/dev/null 2>&1 || die "No container named $EDGE. Name the edge with EDGE_NGINX=<name>."
SITES="$(mount_source /etc/nginx/sites-enabled)"
LETSENCRYPT="$(mount_source /etc/letsencrypt)"
WEBROOT="$(mount_source /var/www/certbot)"
{ [ -n "$SITES" ] && [ -n "$LETSENCRYPT" ] && [ -n "$WEBROOT" ]; } \
  || die "$EDGE does not mount sites-enabled, /etc/letsencrypt and /var/www/certbot: nothing was changed."
docker exec "$EDGE" wget -q --spider -T 5 http://verity-site/ \
  || die "$EDGE cannot reach verity-site. Run infra/scripts/deploy-site.sh first: nothing was changed."

say "Certificate for $HOST"
if [ -f "$LETSENCRYPT/live/$HOST/fullchain.pem" ]; then
  echo "already issued"
else
  # The edge's port 80 block serves /.well-known/acme-challenge/ from this webroot for any
  # hostname, so the challenge needs no config change first.
  docker run --rm -v "$LETSENCRYPT:/etc/letsencrypt" -v "$WEBROOT:/var/www/certbot" \
    certbot/certbot certonly --webroot -w /var/www/certbot -d "$HOST" \
    --non-interactive --agree-tos ${CERTBOT_EMAIL:+--email "$CERTBOT_EMAIL"}
fi

say "Server block"
case "$HOST" in
  *.sslip.io|*.nip.io)
    HEADERS='    # A temporary address: keep it out of search results.
    add_header X-Robots-Tag "noindex, nofollow" always;' ;;
  *)
    HEADERS='    add_header Strict-Transport-Security "max-age=31536000" always;' ;;
esac
config="$(<"$TEMPLATE")"
config="${config//@HOST@/$HOST}"
config="${config//@HEADERS@/$HEADERS}"

CONF="$SITES/website"
# Kept beside sites-enabled, not in it: everything in sites-enabled is loaded.
PREVIOUS="$(dirname "$SITES")/website.previous"
had_previous=0
if [ -e "$CONF" ]; then cp -a "$CONF" "$PREVIOUS"; had_previous=1; fi
printf '%s\n' "$config" > "$CONF"
if ! docker exec "$EDGE" nginx -t; then
  if [ "$had_previous" = 1 ]; then mv "$PREVIOUS" "$CONF"; else rm -f "$CONF"; fi
  die "nginx rejected the new block and it was removed again. The edge is as it was."
fi
rm -f "$PREVIOUS"
docker exec "$EDGE" nginx -s reload
echo "installed $CONF and reloaded $EDGE"

say "Checks"
sleep 1
via() { curl -s --max-time 15 --resolve "$1:443:127.0.0.1" "${@:2}"; }
echo "https://$HOST/               $(via "$HOST" -o /dev/null -w '%{http_code}' "https://$HOST/" || true)"
echo "https://$HOST/robots.txt     $(via "$HOST" "https://$HOST/robots.txt" | head -1 || true)"
echo "https://$PLATFORM_HOST/      $(via "$PLATFORM_HOST" -o /dev/null -w '%{http_code}' "https://$PLATFORM_HOST/" || true)   (the platform, as before)"

say "Done"
echo "Expect 200, 'User-Agent: *' and 200. Open https://$HOST/"
