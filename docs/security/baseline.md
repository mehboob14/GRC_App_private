# Security baseline

The platform sells trust. Every item here is a product property, not an internal preference.

## Access control

- RBAC with least-privilege roles and granular per-module, per-action permissions.
- **Every route declares its required permission.** No implicit allow, no authenticated-only default.
- Object-scoped access (control owner, time-boxed auditor) is application logic layered on top of the
  flat permission check. The flat model does not deliver row-level scoping — do not assume it does.
- Administrative accounts require MFA.
- Auditor access is read-only, scoped to an engagement, and expires with its window — enforced at
  query time, not by a nightly job.

## Tenant isolation

See [multi-tenancy.md](../architecture/multi-tenancy.md). App filter plus RLS plus an automated
isolation test on every change. A cross-tenant read is the highest-severity bug class in this
codebase.

## Secrets

- Connector credentials, MFA secrets, and portal tokens are encrypted at the application layer before
  reaching the database.
- Never in logs, exception messages, `__repr__`, or error responses.
- Pre-commit secret scanning; CI secret scanning; failures are never bypassed.
- Rotation is possible without downtime, and credential expiry is surfaced in the connection health
  view before it breaks a sync.

## Input and output

- Validate every input at the boundary with Pydantic. Client-side validation is UX only.
- Parameterised queries always. String-built SQL is never acceptable, including in migrations and
  admin scripts.
- Rich-text document content is sanitised **server-side** before storage, and still treated as
  untrusted on render.
- Uploads: type and size validated, content hash recorded, stored outside the web root, served
  through short-lived signed URLs. Never trust a client-supplied filename or content type.
- Errors return no internals. Correlation id in, detail in the logs.

## Transport and headers

TLS everywhere. HSTS, `X-Content-Type-Options`, `Referrer-Policy`, frame denial, and a CSP with no
inline script. Rate limiting on all authenticated routes, tighter on auth and portal-token routes.

## Audit trail

Every state-changing action: actor, timestamp, before and after. Append-only, exportable, never
editable. This is the artifact an auditor asks for first.

## Data handling

Client data and evidence remain within the organisation's deployment. Retention defaults to audit
period + 1 year, configurable. `legal_hold` exempts an item from deletion. Deletion of compliance
objects is a status change with justification, never a row removal.

## Dependencies

Lockfiles committed. Automated vulnerability scanning on every build. A new dependency needs a
stated reason: what it replaces and why it is worth the supply-chain surface. Prefer the standard
library and boring, maintained packages.

## The uncomfortable question to ask of every change

*If this code is wrong, can one tenant see another tenant's data, or can an auditor be shown
something untrue?* If either answer is yes, it needs a test that proves otherwise.
