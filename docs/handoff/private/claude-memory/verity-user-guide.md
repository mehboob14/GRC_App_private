---
name: verity-user-guide
description: End-user documentation for Verity — where it lives, how the screenshots are produced, and which screens are mock
metadata:
  type: project
---

Built 2026-09-26 (commit 61929d1). `docs/user-guide/`: README.md plus 13 chapters, 43
screenshots in `images/`, and `verity-user-guide.html`, one page generated from the
markdown by scratchpad `build_guide_html.py`. Published as an artifact:
https://claude.ai/artifact/FGMUontY9EAXzr6d7fmBvy

**How the screenshots were produced** (repeat this when they need refreshing):
1. Isolated database `verity_guide` on the WSL cluster (5433), so the user's own
   `verity` DB is untouched. Create it, run the init grants for `verity_app`,
   `alembic upgrade head`, `seed-content`.
2. `scripts/week5_vendor_demo.py` for the vendor portfolio, then scratchpad
   `seed_guide.py <admin email>` for assets, vulnerabilities, risks, documents,
   tasks, evidence and control owners.
3. `memory/cdp_shot.py` (headless Chrome over CDP at 1440x900) driven by scratchpad
   `make_steps.py <batch>`; `shot_any.py` is the variant whose `goto` takes a full URL.

**Gotchas found doing it:**
- The in-app preview browser refuses page tools on any URL it considers a local file,
  including `127.0.0.1:<port>` that it did not start. Use the CDP script instead.
- `/risks/library` and `/risks` both require `register_id`.
- Task `category` is security/privacy/operations/data/regulatory/vendor/other.
- An unknown `evidence_type` on `POST /evidence/link` escapes as a 500 (CHECK
  violation) rather than a typed error. Worth fixing.
- week5_vendor_demo occasionally 404s on the tiering call right after creating a
  vendor: the response can reach a fast client before the session commits. Re-running
  it succeeds.

**Honest notes the guide makes:** `/dashboard` is a static design mock (no queries,
invented ISO 27001 and HIPAA rows); Get Started IS live (`useQueries`, which a grep
for `useQuery` misses).

Related: [[verity-grc-platform]], [[verity-vendors-module]], [[verity-assets-module]].
