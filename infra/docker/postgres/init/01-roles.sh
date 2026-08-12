#!/bin/bash
# Create the roles the application and the read-only consumers connect as.
#
# The application must never connect as the schema owner. An owner is exempt from
# ENABLE ROW LEVEL SECURITY unless the table also carries FORCE, so an application
# running as the owner is protected only by every migration having remembered FORCE —
# and one forgotten FORCE opens everything (docs/architecture/multi-tenancy.md).
#
#   verity_owner (POSTGRES_USER)  owns the schema, runs migrations
#   verity_app                    owns nothing, NOBYPASSRLS, used by the API and workers
#   verity_readonly               SELECT only, RLS still applies
#
# Runs once on an empty data directory. Every statement is guarded, so running it by
# hand against an existing cluster is safe.

set -euo pipefail

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set ON_ERROR_STOP=on \
  --set owner_user="$POSTGRES_USER" \
  --set app_user="${VERITY_APP_USER:-verity_app}" \
  --set app_password="${VERITY_APP_PASSWORD:-verity_app}" \
  --set readonly_user="${VERITY_READONLY_USER:-verity_readonly}" \
  --set readonly_password="${VERITY_READONLY_PASSWORD:-verity_readonly}" <<'SQL'

-- Postgres has no CREATE ROLE IF NOT EXISTS, so the statement is generated only when
-- the role is absent and executed with \gexec. format's %I and %L quote the identifier
-- and the literal, so neither a role name nor a password can break out of the statement.
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT',
    :'app_user', :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT',
    :'readonly_user', :'readonly_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'readonly_user')
\gexec

-- Nobody creates objects in public except the owner. Without this, any role can create
-- a table there, and a table created outside a migration has no RLS policy on it.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;

GRANT CONNECT ON DATABASE :"DBNAME" TO :"app_user";
GRANT CONNECT ON DATABASE :"DBNAME" TO :"readonly_user";
GRANT USAGE ON SCHEMA public TO :"app_user";
GRANT USAGE ON SCHEMA public TO :"readonly_user";

-- No tables exist yet; migrations create them. Default privileges mean a table the
-- owner creates tomorrow is already usable by the application, rather than needing a
-- follow-up grant somebody would forget. Each migration still grants explicitly
-- (verity.db.rls.grant_crud) so a table's privileges are visible where it is defined.
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_user" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_user" IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_user" IN SCHEMA public
    GRANT SELECT ON TABLES TO :"readonly_user";

-- Append-only tables (audit_log, task_transitions, vuln_transitions, check_results,
-- readiness_snapshots, kri_measurements, document_versions) take UPDATE and DELETE back
-- from the application role in their own migration, via
-- verity.db.rls.make_append_only. Immutability is a property this product sells to an
-- auditor, and docs/conventions/database.md requires a revoked grant rather than a
-- convention: a refused UPDATE is evidence, a code review is not.

SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname IN (:'owner_user', :'app_user', :'readonly_user')
ORDER BY rolname;

SQL

echo "roles ready"
