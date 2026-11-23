---
name: verity-preview-browser-login
description: "How to log the Verity web app into a session in the in-app preview browser (MSW doesn't intercept there)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 70afa149-15c7-47ca-91dd-848cdb9d5ba4
  modified: 2026-08-13T18:36:51.442Z
---

In the HP dev env, the in-app preview browser's MSW service worker does **not** intercept —
`/api/v1/_mock/health` 404s and every request passes through the Vite proxy to the **real
backend on 8001**. So browser verification runs against real data, not mock fixtures (the
`alex.okafor@northwind.cloud` fixtures don't exist in the real DB).

Two gotchas when driving the app via the browser tools:
- `form_input` (programmatic value set) does **not** update React Hook Form state → the form
  submits empty and 401s. Use real keystrokes (`computer` type) **or** bypass the form entirely.
- `computer left_click` by `ref` sometimes doesn't land in the headless pane; a DOM
  `element.click()` via `javascript_tool` is reliable (fires React onClick, opens Radix dialogs,
  selects Radix `[role=option]`s).

**Deterministic login** (bypasses the flaky form): POST `/api/v1/auth/login` via fetch, then
inject the session into `sessionStorage` and reload:
```js
sessionStorage.setItem('verity.session.token', j.access_token)
sessionStorage.setItem('verity.session.principal', JSON.stringify(j.principal))
```
Keys are defined in `frontend/src/lib/auth/session.ts`. Navigating after that boots the app authenticated.

To make a **verified admin** in the real DB without clicking an email link: mint an
`email_verify` token with `issue_token(subject=<user_id>, plane="tenant", typ="email_verify")`
(backend venv, loads root `.env` for SECRET_KEY), POST it to `/auth/verify-email` → returns a
session. See [[verity-grc-platform]] and the always-restart-API rule.
