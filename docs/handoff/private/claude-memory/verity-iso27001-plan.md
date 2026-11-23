---
name: verity-iso27001-plan
description: 2026-10-10 ISO 27001:2022 plan (uncommitted): docs/product/iso27001-plan.md + draft crosswalk CSV, Probo findings, draft numbers, the 4 code blockers, GitHub impact, open decisions
metadata:
  type: project
---

Written after the Faheem call (ISO is Phase 3.1, priced separately; he will check Phase 1 against the document first). Files, both untracked: `docs/product/iso27001-plan.md` and `docs/product/iso27001-draft-crosswalk.csv` (123 rows; draft, unreviewed, FW-5). "Following probe" was read as Probo.

Probo (MIT): `apps/console/public/data/frameworks/ISO27001-2022.json` is 123 entries, id and name only (30 clause items + 93 Annex A); `data/mitigations.json` has 81 measures with `standards` strings but poor mappings (encryption to A.8.11 not A.8.24, coarse clause ids, 34 of 123 items unreferenced), only 3 keys equal ours. Use as input, never as the crosswalk.

Draft numbers (my crosswalk): 59 covered, 45 partial, 18 need a new control, 1 organisational; 113 of 116 controls serve both frameworks (SOC 2 only: GOV-12, SD-07, SD-08); 16 new controls (GOV-23 to GOV-33, LM-12, DM-18, DM-19, NS-12, EP-07); 26 controls have SOC 2 only wording. GitHub's 7 checks reach 11 ISO requirements (4 main) vs 5 SOC 2 criteria; no change to them, add code scanning + unreviewed merges, propose repo access, SSO, push protection, audit log.

Code blockers before ISO can load: Engagement is one per tenant with type_1/type_2 and TSC scope; loader requires `trust_services_category` and `is_always_in_scope`; `instantiate_library` adopts every pack's templates (signup, POST /controls/adopt, backfill_adopt_soc2) and never links already adopted controls to a new framework; AI prompt, emails and report labels say SOC 2.

**Why:** the user wants ISO planned with common controls and the effect on guidance and GitHub checks.
**How to apply:** stage A (groundwork) can sit in Phase 2; pack and SoA are Phase 3.1; estimate about 7 weeks one developer plus a reviewer. Open decisions are in section 9 of the plan (price/date, second reviewer, buy ISO 27001/27002, titles, inherited status, one scope or two, HR and MDM connectors). See [[verity-multiframework-design]], [[verity-common-control-framework]].
