---
name: verity-demo-request-flow
description: "Website /demo/ page plus public POST /api/v1/public/demo-requests (stored, audited, emailed to the owner); built and verified end to end 2026-10-06, committed only on the user's go; deploy order and settings"
metadata:
  node_type: memory
  type: project
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-06T14:43:51.259Z
---

2026-10-06: the website's demo popup was replaced by a `/demo/` page (full name, work email, company, one optional message; everything else is settled by email) and a public endpoint `POST /api/v1/public/demo-requests` (module `backend/src/verity/modules/leads`, provider-plane table `demo_requests`, migration `61e2554a5209` after `b4e1f9a2c7d3`). Each request is stored and audited in the provider stream (id and three labels, no personal data), then after the response the owner is mailed at `LEADS_NOTIFY_EMAIL` (default `mehboobarshad300@gmail.com`, Reply-To = the visitor) and the visitor gets a generic receipt at most once per address per 24h (`LEADS_CONFIRM_REQUESTER`). Limits: 5 per hour per address, 3 per day per email, 300 per day overall. CORS only on that route (`ScopedCorsMiddleware`, `LEADS_ALLOWED_ORIGINS` = JSON list of exact origins).

**State (2026-10-06, after the user said go):** committed and pushed, not yet deployed. `feat/phase1-completion` is at `c9a796b`: `403af77` leads (also carries the rate-limit address safeguard), `089a987` dashboard coverage card, `c9a796b` deploy.sh now reloads `verity-web` and the edge nginx after the swap and prints a public check (this is what prevents the post-deploy 502). `feat/website-deploy` is at `33df557`: `4750342` demo page, `33df557` docs defaults. The user still has to run the server steps (platform first, then site). Tooling in the scratchpad: `platform_commit.py` and `site_sync_commit.py` (both build commits through a temporary index; the working copy of the site is `scratchpad/site-work`).

**Deploy order:** platform first (migration runs in `deploy.sh`; add `LEADS_ALLOWED_ORIGINS=["https://website.37-60-228-227.sslip.io"]` to `.env.production`; real `SMTP_*` needed or requests are stored with no mail), then the site (`deploy-site.sh`; the image defaults `NEXT_PUBLIC_DEMO_ENDPOINT` to `APP_URL` + the path and adds that origin to the CSP). Change the allowed origin together with `SITE_URL` when the real hostname exists.

**Flagged to the user:** the copy "usually within one business day" (in `website/content/demo.ts` and the receipt in `leads/service.py`); the receipt mail is on by default; the consent checkbox became a notice line; the notify address is also the default in code.

**How it was verified:** headless Chrome (Playwright with the local Chrome) to a real API on `verity_test` to an SMTP sink, including the browser CORS preflight, a 429 and the honeypot. Run such local mail tests from a folder with no `.env` above it: `backend/.env` holds real SMTP credentials and the app will try to authenticate with them. Related: [[verity-website-deploy]], [[feedback-backslashes-in-bash-python]].
