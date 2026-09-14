# Risk register decisions

Each item is a place where the signed documents are silent, disagree, or were extended by the
product owner. Each states the reading taken and what it costs to revisit. **Load bearing** means
expensive to change once a tenant has data.

| | Decision | Load bearing | Taken |
|---|---|---|---|
| R1 | One matrix per tenant or per register | ●●● | Per register |
| R2 | Score formula | ●● | Likelihood × impact |
| R3 | Severity bands | ● | Per register thresholds on the score |
| R4 | Status vocabulary | ●●● | open, in_treatment, mitigated, accepted, closed |
| R5 | Treatment versus status | ●● | Separate fields |
| R6 | Who approves an acceptance | ●● | A named approver who is not the requester |
| R7 | What expiry does | ●● | Expire the acceptance, reopen the risk, notify |
| R8 | Business unit | ● | An IAM group |
| R9 | Treatment actions | ● | Tasks, linked with `remediates` |
| R10 | Categories | ●● | Rows per register, two levels |
| R11 | Library adoption | ● | Copy text, link suggested controls |
| R12 | AI assist without a model | ● | Closest library match |
| R13 | Import | ● | Stateless preview, then commit valid rows |
| R14 | Codes | ● | RSK-0001, per tenant |
| R15 | Phase 3 tables | ● | Designed, not migrated |
| R16 | Register type on the risk | ● | A property of the register |

## R1. The matrix belongs to the register

ER 3.6 draws `RISK_MATRIX_SETTINGS` keyed by `tenant_id`: one matrix per workspace. The product
owner asked for several registers configured independently (the Vanta and Drata baseline), and a
5×5 enterprise register next to a 3×3 project register is ordinary. So the matrix columns move onto
`risk_registers`. A tenant with one register sees exactly the ER's behaviour.
Revisit cost: merging registers later needs a rescale of stored scores.

## R2. Score is likelihood × impact

The ER states the product and GRC-Tenant computes the same. Stored as generated columns so the
register sorts and filters on it without recomputation. Custom formulas (weighted, additive, FAIR)
are a Soon item. Revisit cost: a new formula is a new generated expression and a migration.

## R3. Bands are thresholds on the score, per register

Each register stores ascending bands `{key, label, min_score}` over low, medium, high, critical.
Defaults for 5×5: low 1, medium 5, high 10, critical 15. Other sizes scale the thresholds to the
maximum score. Shrinking a matrix below a stored score is refused rather than silently clamped.

## R4. Five statuses

The ER lists open, accepted, closed. GRC-Tenant adds in_treatment and mitigated, and the product
owner's form shows Status with Open as the default. The five state set is taken because
"treatment underway" and "treated, now monitored" are the two states a reviewer filters on most.
`accepted` is reachable only through an approved acceptance; `closed` requires a justification (a
database CHECK). Revisit cost: a status rename is a data migration.

## R5. Treatment is not status

Choosing "accept" as the treatment decision records intent; it does not make the risk accepted.
Acceptance needs its own approval (R6). This is what stops a dropdown from standing in for a
signature.

## R6. The requester cannot approve

The spec requires "formal acceptance with approver, rationale, expiry". The vendor gate (V4) and
the vulnerability exception flow already refuse self approval, and an auditor reads an acceptance
approved by its own requester as no acceptance. So the approver is named on the request, must
differ from the requester, and only that person (holding `risks:approve`) can decide. The risk
owner **may** approve: ISO 27001 6.1.3 f asks risk owners to accept residual risk. A one person
workspace cannot accept its own risks, which is the same consequence V4 already accepts.

## R7. Expiry reopens

ER prose: an expired acceptance reopens the risk through a scheduled job. The job marks the
acceptance expired, moves the risk from accepted to open, writes a history event and an audit row
as the system actor, and notifies the owner once. Revoking does the same immediately.

## R8. Business unit is a group

The product owner asked for the group dropdown to act as department and business unit. GRC-Tenant
builds "Assigned team / department" on its teams, which map to Verity's IAM groups. So
`risks.department_group_id` references `groups` and the field reads "Business unit".

## R9. Treatment actions are tasks

Vanta's action tracking and GRC-Tenant's mitigation actions both need owners, due dates, status and
reminders, which the task module already has with SLAs and history. Adding an action creates a
task (`raised_from_type = risk`) and links it with `remediates`. No action table.

## R10. Categories are rows

Two levels in one table (`parent_id` null is a category). Rows rather than JSON so a rename
propagates to every risk and a category in use can be archived instead of deleted. Each new
register starts with the default taxonomy: Strategic, Operational, Financial, Compliance,
Technology, Third party, Project and change, Internal, each with its sub-categories.

## R11. Library adoption copies

The same rule as control templates: a library update must never rewrite a risk someone reviewed.
Adoption copies the text, keeps `template_id` for ancestry, rescales default scores to the
register's matrix, maps the category by name, and links the suggested controls the workspace
already has. Content is Verity authored; no third party library text is reproduced.

## R12. AI assist degrades to the library

With a model key the prompt returns a JSON draft constrained to the register's taxonomy and scale.
Without one, or on any failure, the draft comes from the library template closest to the title by
term overlap. The response says which (`ai` or `library`). Nothing is written by either path.

## R13. Import previews first

The file is parsed server side (CSV or Excel) into normalised rows with per row errors. The client
shows the preview and sends back the rows it wants; the service validates again and creates only
valid rows. No upload is stored and nothing is written by the preview.

## R14. Codes are per tenant

`RSK-0001` from max plus one with a retry on the unique constraint, as tasks do. Per tenant rather
than per register so a code stays unique in exports and links that span registers.

## R15. Phase 3 tables are not migrated

RCSA, risk assessments, KRIs, appetite, incidents and workflow tables are designed in ER 3.12. The
delivery plan says build the phase you are in and design for all three. They are described in the
requirements addendum and appear as Soon in the interface.

## R16. Register type lives on the register

GRC-Tenant puts register type on each risk. With several registers the type is a property of the
register (an ISO 27001 register holds ISO 27001 risks), so the form asks for the register and shows
its type. A single register workspace loses nothing.
