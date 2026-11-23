---
name: verity-commercial-thread-2026-10
description: "2026-10-04 Faheem asked about the user guide and ISO 27001; what the signed plan puts in scope, and the marketing website built unrequested"
metadata:
  node_type: memory
  type: project
  originSessionId: 45b4862f-d2c7-4fc0-8ebb-c7559780cba8
  modified: 2026-10-06T11:17:38.999Z
---

On 2026-10-04 Faheem asked about end-user documentation and ISO 27001 (the user said both were in the initial scope). The signed spec and the 8 week build plan (both docx) list neither the user guide nor a website. ISO 27001, HIPAA and GDPR are Phase 3 deliverable 3.1, and the build plan says Phases 2 and 3 are "scoped and priced separately as we reach them". `docs/product/delivery-plan.md`: anything not in a phase is "scoped separately and agreed before any work starts".

The user also built Faheem a marketing website for Verity, apparently unrequested, and is unsure how to get paid for it. Payment terms and what has been paid so far are not visible to me.

**Why:** the user asked how to reply and how to get paid; advice depends on this scope position.

**How to apply:** never treat the website or guide as billable unless Faheem asked for them. For an ISO estimate use tasks E1 to E3 in `openspec/changes/common-control-framework/tasks.md` (no ISO pack exists yet; the engine is ready and a second pack provably leaves SOC 2 untouched). ISO text is licensed: identifiers plus own summaries, legal review of titles. Client messages stay short, casual, no dashes ([[deploy-and-client-comms-style]]). Phase 1 was not sign-off clean on 3 Oct ([[verity-spec-gap-2026-10]]); the backup and restore demo is the visible gap. Framework design: [[verity-multiframework-design]].

**Later the same day:** the contract is on Upwork, Faheem handles money talk, Shehzad normally sends proposals. The user plans to announce Phase 1 done in the main group, mark the Upwork milestone, then pitch the website and ISO (ISO is Faheem's lower priority). The site is `website/` (Next.js) on `codex/public-website`, pushed to origin. It marks features live or soon, shows no prices (the tiers are a proposal for Faheem to confirm) and lists ISO as soon. The GitLab snapshot c34b94d has no `website/`; keep it out of any re-snapshot until terms are agreed. Three website commits (b58f74a, 154af91, 7b184ca) are authored "Claude", against the mehboob14 rule, so hand over a clean snapshot, not history. Advice given: do not declare Phase 1 done until the exit criteria can be demonstrated, show the website instead of asking whether they want one, and offer a fixed price launch package as an Upwork milestone. Website price advice (USD, my judgment, Phase 1 price unknown to me): ask 3,500, settle 2,500 to 3,000, floor 1,800, cut scope not price below 2,500, below the floor offer it bundled with ISO; sanity check is about a fifth to a quarter of Phase 1's price. The site is static Next.js with 50 docs articles, a 60 framework library, 5 industries, pricing, security and a demo form.

**2026-10-06:** the user said Phase 1 is done. Site and docs are live at the temporary `https://website.37-60-228-227.sslip.io/` (docs at `/docs/`, noindex, deployed as the `verity-site` container from branch `feat/website-deploy`, runbook `docs/runbooks/website.md` on that branch). A real hostname needs a DNS record plus root running `edge-add-website.sh`. In git, `feat/phase1-completion` (trace, audit export, backup and deploy scripts, review reminders) was still not merged to main, so the server may lack it. Message drafted: group gets Phase 1 plus the docs link, Faheem gets the website and ISO lines. The user then chose: both links go in the main group, and the website price stays open ended with Shehzad on WhatsApp (no number in either message; the $800 floor stays private).
