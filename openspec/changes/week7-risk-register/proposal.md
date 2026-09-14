# Risk register: multiple registers, a configurable matrix, acceptance with expiry

## Why

SOC 2 CC3.1 to CC3.4 ask a company to identify, analyse and respond to risk, and ISO 27001 clause
6.1 asks the same with a named owner who accepts the residual risk. Verity already ships the
controls, evidence, vendors, assets and vulnerabilities those answers point at, but there is no
place to record the risk itself. The Risks item in the navigation says Soon. This change closes it.

The signed specification describes the register in one sentence, and that sentence is the scope:

> Deliverable 1.2: "identify and record the risk, score inherent likelihood and impact, link the
> controls that mitigate it, decide the treatment, record the residual score, and revisit on
> scheduled review dates."

Around it the spec asks for a configurable likelihood by impact matrix, an owner, a category and a
treatment (mitigate, accept, avoid, transfer), a flag on any risk with no linked control, formal
acceptance with an approver, rationale and expiry where an expired acceptance reopens the risk, a
starter risk library, a heatmap and treatment status export, promotion of vendor findings into the
register, and the 360 degree trace from vulnerability to asset to risk to control.

The product owner added what a production register needs on top of the spec, benchmarked against
Vanta Risk and Drata Risk Management and against the GRC-Tenant product the team already runs:
several registers configured independently, categories with sub-categories that follow the chosen
category, a business unit taken from the workspace's groups, linked assets on the form, root cause,
consequences, recommendations and a treatment plan, AI assist on the title, and spreadsheet import
with a downloadable template.

## What this change delivers (Phase 1, built now)

- **Registers.** A workspace keeps as many registers as it needs (enterprise, ISO 27001, SOC 2,
  PCI DSS, SOX, GDPR, RCSA, project, third party...). Each owns its own matrix size and level labels,
  severity bands, category taxonomy and review cadence. A default register exists from first use.
- **The risk.** Title, description, category and sub-category, status, business owner, business
  unit (an IAM group), inherent and residual likelihood and impact with computed scores and bands,
  root cause, consequences, recommendations, treatment decision, treatment plan and due date, next
  review date, origin (manual, library, import, vendor finding) and the integration triple.
- **Linkage.** Controls through an explicit join table (ER RISK_CONTROL_MAP). Assets,
  vulnerabilities, evidence, tasks and issues, vendors and documents through the links primitive.
  "No linked control" is computed, never stored.
- **Treatment actions** are tasks. Adding one creates a task that remediates the risk, so SLAs,
  assignees and status come from the task module rather than a second tracker.
- **Acceptance with expiry.** Requested with an approver, rationale and expiry; decided by the
  approver, never by the requester; revocable. A daily job expires lapsed acceptances and reopens
  the risk, and tells the owner.
- **Reviews.** Mark reviewed moves the next review date by the register's cadence. Overdue reviews
  show on the overview and notify the owner.
- **Starter library.** A Verity authored global library of about sixty risks, each with default
  scores, narrative and suggested SOC 2 controls. Adopting copies the text and links the controls
  the workspace has.
- **AI assist.** From a title, draft the description, root cause, consequences, recommendations,
  category and scores. Drafts only (rule 11): nothing is saved until a person applies a field and
  saves. Without a model key it falls back to the closest library match.
- **Import and export.** An Excel template with dropdowns (sub-category follows category), a
  preview that validates every row before anything is written, and CSV or Excel export with the
  register, both heatmaps and treatment status.
- **Overview.** Attention tiles, inherent and residual heatmaps whose cells filter the register,
  top risks, treatment status and category breakdown.
- **Vendor finding promotion** through the seam `vendor_findings.promoted_risk_id` already ships.

## Visible now, built later (shown with a Soon marker, not functional)

Risk assessments and RCSA campaigns, key risk indicators, risk appetite and tolerance, incidents,
multi step approval workflows, register snapshots, board and PDF reports, custom fields, custom
scoring formulas, quantification, continuous control monitoring signals on a risk, register level
permissions, AI mitigation plans. The requirements for each are written in
`docs/product/risk-management-requirements.md` so the phases after this one start from an agreed
reading rather than a blank page.

## Out of scope

Anything in Phase 3 (deliverable 3.1) beyond the Soon markers. The Phase 3 tables are designed in
the ER already; they are not migrated now because the delivery plan says build the phase you are in.

## Impact

- 7 new tables: 6 tenant owned with forced RLS (`risk_registers`, `risk_categories`, `risks`,
  `risk_control_map`, `risk_acceptances`, `risk_events`) and 1 global (`risk_templates`).
- 4 permission keys: `risks:read`, `risks:manage`, `risks:approve`, `risks:configure`.
- Notification kinds for acceptance and review, plus the two vendor kinds the vendor jobs already
  send and the database constraint refused (a latent failure fixed in the same migration).
- One daily worker job. One content pack (`risk_library`).
- Frontend: the Risks module (overview, register, library, settings), risk detail page, risk form
  popup with AI assist, import dialog, and the promote action on vendor findings.
