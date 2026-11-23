---
name: verity-error-handling
description: "Production-grade error handling pass: 191 backend raises given reader copy, network/timeout as ApiError, describeError single source of truth, ErrorBoundary, smart retry"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-09-02T18:14:40.560Z
---

**VERITY ERROR HANDLING (2026-09-02).** User was angry about the sign-in error reading
"Sign-in failed / Sign-in refused: the password is incorrect (this detail is shown in development
only)." and demanded production-grade errors "accross the platform, if something not loads,
fails, on signup, login pages all". See [[verity-ui-consistency-primitives]].

## The root cause (measured, not guessed)

`VerityError` carries `message` (sent to the client, SHOWN TO A HUMAN) and `detail` (logged only,
`core/errors.py::_response` sends message alone). **191 of 198 domain raises passed only
`detail=`**, so the actionable sentence went to the log and the reader got the class default:
`InvalidInput` -> "The request could not be processed as submitted.", `AuthenticationRequired` ->
"Authentication is required." A wrong MFA code literally said "Authentication is required."
After the pass: **180 raises carry reader copy** (was 7).

The ~33 still on class defaults are deliberate: `core/deps.py` + `core/security.py` auth guards
(the frontend overrides 401/403/404 with better copy so those defaults never surface), and the
invite / password-reset / email-verify paths, which are kept UNIFORM on purpose because an invite
token is a bearer credential and per-reason copy is an enumeration oracle. `InvalidInvite` even
documents this. Do not "improve" those.

## Frontend foundation (src/lib/api/)

- **`fetch` was never wrapped**, so offline/DNS/server-down threw a bare `TypeError`. Every call
  site is `e instanceof ApiError ? e.message : "<generic>"`, so the most common production
  failure hit the generic fallback. Now `ApiError.network()` / `ApiError.timeout()` are
  **ApiError instances with status 0**, which fixed ~100 call sites without editing them.
  Also added AbortController timeouts: 30s normal, 300s for FormData uploads.
- **`describe-error.ts` is the single source of truth** for what a user reads.
  `describeError(error, subject?)` -> `{kind, title, message, retryable, referenceId}`.
  Key split: INFRASTRUCTURE failures (network/timeout/5xx) get our copy; DOMAIN failures
  (400/409/422) pass the server message through, because those are now written for readers.
  403/404 return `retryable: false` so no pointless "Try again" button.
  `describeAuthError(error)` is separate because **a 401 on a login form means bad credentials,
  not an expired session** (the generic mapping would say "your session has ended").
- **`ErrorBoundary`** (src/components/error-boundary.tsx) wraps the app inside `<BrowserRouter>`;
  there was none, so any render crash white-screened. Resets on `location.pathname` change so the
  reader is not trapped. Router is `<BrowserRouter>`, NOT `createBrowserRouter`, so there is no
  `errorElement` available.
- **Query retry** was a blanket `retry: 1` (retried 403/404 pointlessly, gave network blips one
  try). Now retries only `error.retryable` up to 3 with exponential backoff; mutations never
  auto-retry (a write could double-apply).
- Query files handling errors went **24/50 -> 49/50** (the 50th is a false positive: my grep
  matched `useQueryClient`).

## Gotchas worth keeping

- **Do NOT trust `npx tsc --noEmit`** here: root `tsconfig.json` is a solution file with
  `"files": []`. Use `npx tsc --noEmit -p tsconfig.app.json`, or the project's own
  `npm run typecheck` / `npm run build` (both are `tsc -b` and ARE correct). Three invalid
  `Badge` variants sat in HEAD unnoticed because the typecheck was not being run before commit.
- Testing a module in the Vite dev browser: `import('/src/x.ts')` and the `@/`-aliased specifier
  resolve to **different module ids** (`?t=<ts>`), so `instanceof` fails across them and every
  branch looks broken. Read the transformed source and import the exact specifier it uses.
- Editing files under a live dev server leaves stale HMR 500s in the console that do not
  reproduce on reload; confirm with `npm run build` before believing them.
- 5 Alembic migrations share a pre-existing `Column` type-arg mypy error (4 predate this work).
  `uv run mypy src/verity/modules src/verity/core` is clean; full `src/verity` is not.
- Frontend has **no test framework** (no vitest, zero tests). Adding one needs the dependency
  flagged per CLAUDE.md, so it was not done unilaterally.

## Verified live

Backend restarted on :8001. `POST /auth/login` with a wrong password AND with a non-existent
account both return byte-identical `"Incorrect email or password."` (no enumeration), while the
server log carries `login.refused reason='...'` against the same `correlation_id` the user would
quote. `describeError` mapping verified in-browser across network/timeout/403/404/429/500/409/422
plus a raw TypeError.
