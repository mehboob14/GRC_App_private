#!/usr/bin/env bash
# Run the owner's Keycloak build locally for Verity's SSO work (openspec/changes/add-keycloak-sso).
# Local development only: dev mode, H2 file store, throwaway admin. Verity never runs Keycloak in production.
#
#   bash infra/keycloak/run-local.sh          # start (imports the realms on first run)
#   python infra/keycloak/setup_local.py      # then, once it is up: organization, domain, IdP link
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
KC_HOME="${KC_HOME:-/c/Development/keycloak-local/keycloak-999.0.0-SNAPSHOT}"
if [ ! -x "$KC_HOME/bin/kc.sh" ]; then
  echo "Keycloak not found at $KC_HOME. Unpack the build first:" >&2
  echo "  unzip C:/Development/Key_cloak/quarkus/dist/target/keycloak-999.0.0-SNAPSHOT.zip -d C:/Development/keycloak-local" >&2
  exit 1
fi
mkdir -p "$KC_HOME/data/import"
cp "$HERE"/realms/*.json "$KC_HOME/data/import/"
export KC_BOOTSTRAP_ADMIN_USERNAME="${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}"
export KC_BOOTSTRAP_ADMIN_PASSWORD="${KC_BOOTSTRAP_ADMIN_PASSWORD:-admin}"
exec "$KC_HOME/bin/kc.sh" start-dev --http-port 8180 --http-management-port 9180 --import-realm
