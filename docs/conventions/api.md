# API conventions

REST over HTTP, JSON only. FastAPI generates the OpenAPI schema; the frontend generates its types
from it. Hand-written client types drift silently and are forbidden.

## Shape

- Resources are plural nouns: `/api/v1/controls`, `/api/v1/vendors/{vendor_id}/engagements`.
- Verbs live in the method, not the path. The exception is a genuine action that is not CRUD:
  `POST /api/v1/vendors/{id}/approve`.
- Nest at most one level. Deeper nesting becomes a query parameter.
- `v1` in the path. Breaking changes get `v2`; additive changes do not.

## Tenancy

**The tenant is never a path or query parameter.** It is resolved from the authenticated session and
verified against the user's actual membership. A `tenant_id` accepted from the client is a critical
security bug — for the provider plane, the operator selects a tenant through an explicit,
audit-logged impersonation flow, not a query string.

## Requests and responses

- Request and response bodies are Pydantic models. ORM objects are never returned directly.
- Lists are paginated by default: `?limit=&cursor=`. Cursor pagination, not offset, because these
  tables grow and offset pagination degrades and skips rows under concurrent writes.
- Filtering and sorting are explicit allow-lists. Never build a query from arbitrary client fields.
- Timestamps are ISO 8601 UTC with a `Z` suffix.

## Errors

One consistent envelope:

```json
{ "error": { "code": "evidence_not_found", "message": "Evidence item not found.", "correlation_id": "01J..." } }
```

- `code` is a stable machine-readable string. The frontend switches on `code`, never on `message`.
- `message` is safe to show a user and **contains no internals** — no SQL, no stack traces, no
  upstream provider text.
- `correlation_id` ties to the server log where the real detail lives.
- 401 unauthenticated, 403 authorised-but-forbidden, 404 for a resource in another tenant (never 403
  — a 403 confirms the resource exists, which leaks across the tenant boundary).
- 409 for state-machine violations, 422 for validation.

## Idempotency

Any endpoint a client might retry, and every connector-facing write, accepts an idempotency key and
deduplicates on it. Ask of every mutating endpoint: what happens if this runs twice?

## Rate limiting and headers

Rate limits on all authenticated routes, tighter on auth and portal-token routes. Security headers
set globally: HSTS, `X-Content-Type-Options`, `Referrer-Policy`, and a CSP that does not permit
inline script.

What is limited today, all in `core/ratelimit.py`:

| Route | Limit |
|---|---|
| Sign in (tenant and provider) | 10 attempts per account per 15 minutes, 100 per client address per 15 minutes; every attempt counts |
| MFA code and enrolment confirm | 10 per login challenge per 15 minutes |
| Signup, password reset, verification resend | 5 per recipient per hour, 30 per client address per hour |
| Vendor portal | per token, see the limits in the module |

A limited call is `429` with code `rate_limited` and a `Retry-After` in seconds. The limiter fails
closed: with Redis down the call is a `503`, not a pass. The client address is read from `X-Real-IP`
(nginx overwrites it) and only when the immediate peer is a private address, so a caller reaching the
API directly cannot choose their own bucket. Keys never hold an email or a token, only a hash.
