# Decisions and open questions

Written 2026-10-11. Two parts: what is decided (and why, so nobody re-litigates it or breaks it by accident) and what is
still open (ask the owner, do not assume). The repo's ADRs (`docs/adr/0001` to `0014`) hold the architectural decisions in
full; this file adds the product and working decisions that never made it into the repo. Add a line whenever something is
decided: date, decision, why.

## Decided

### Scope and commercial boundaries
- Phase 1 is the core platform on manual data, Phase 2 is connectors and automation, Phase 3 is ERM and more frameworks and
  connectors (`docs/product/delivery-plan.md`). Phases 2 and 3 are priced separately; anything not in a phase is agreed before
  work starts. The signed spec and build plan are `.docx` files in `docs/product/`: never edit them.
- The public website, the docs portal and the user guide were not in the signed plan. Never treat them as billable and never
  put prices or commercial terms in code, docs or commits. The owner handles money and client conversations.
- 2026-10-10: the owner asked for ISO 27001 "end to end now" on the one control library, with connectors decided later. It was
  built early (ISO is Phase 3.1 in the plan). That does not mean other Phase 2 or 3 work is approved.

### Compliance model
- **One control library, many frameworks.** A control satisfies requirements in several frameworks and is worked, owned and
  evidenced once. Requirement status comes only from mapped controls; nothing is inferred between frameworks (ADR-0014).
- **Every workspace adopts the full SOC 2 library at signup** (2026-08-17, the Vanta/Drata pattern): 116 controls today, so
  there is something to scope, own and evidence from day one. Adding another framework adopts only what it needs and links the
  controls already run.
- **Mappings carry `coverage` (full or partial) and a written rationale**; the loader refuses mappings without them. A second,
  qualified reviewer must sign a crosswalk (FW-5): until then mappings are unreviewed and must be called that.
- **Readiness is strict and defined once** (`readiness.py`): implemented, evidence that still counts, automation not failing
  or erroring or stale; a requirement is met only when every applicable mapped control is ready (CF-4). Automation can only
  take readiness away. Dashboards and exports both use it. It lowered some dashboard numbers when introduced.
- **Scope models.** SOC 2 elects Trust Services Categories through its engagement. ISO 27001 is in scope unless excluded in the
  Statement of Applicability with a written reason; clauses cannot be excluded; exclusion is per requirement, never per
  control; an exclusion without a reason is refused by a database check. Each framework has its own engagement and scope.
- **Control identity.** Codes are `<PREFIX>-<NN>` by domain (BC, CS, DM, EP, GOV, HR, IAM, LM, NS, PE, SD); GOV was GRC; custom
  controls are `IC-NN`. Seeds key on `canonical_key`, never `code`. Control Type, Sub-type, Design and Automation are
  database constrained vocabularies: forms must source them from the vocabulary endpoint.
- **ISO text is licensed.** The pack carries identifiers and Verity's own wording (`id_only`). Probo (MIT) supplied
  identifiers and a cross check only. The SOC 2 criteria text is verbatim AICPA text: flag it, do not spread it.
- **AI drafts, people approve.** No model writes to a compliance object, publishes, changes a control state or closes a finding.
  Evidence and connector output are untrusted input to a prompt. With no LLM key a rule based matcher runs, and says so.
- **`error` is not `fail`.** A broken connector must never look like a failed control.
- **Verity's built-in checks are always on** (ME-1, 2026-10-16): provider `verity`, no credential, cannot be
  disconnected. Automation can only take readiness away; reports Verity files itself never count as evidence for
  readiness or for the checks. Owners count only when they are active members. 12 month floors: approvals,
  undated evidence (for the check only), risk assessment, internal audit and management review. The SoA check fails
  an Annex A decision with no reason, inclusions included, although the dialog marks the reason optional.
- **A severity raised on re-import shortens the SLA of open findings** from first detection, never lengthens it,
  audited (2026-10-19). The anchor is open (below).
- **Evidence.** One evidence file per automated check, linked only to the controls that check supports. Connector evidence is
  valid 7 days; the "aging" window is the smaller of 30 days and a third of the item's life; an automated result older than
  48 hours is `stale` and blocks readiness. Evidence lapsing raises one renewal task per manual item only.

- **Guided onboarding decisions of 2026-11-23** (owner, by click): D-4 keep the AICPA criterion text for now; D-5 ship the
  Openlane rewrites as unreviewed drafts; D-8 show the country law entries in production with the disclaimer; D-9 engage
  an ISO 27001 lead auditor and a SOC 2 CPA as reviewers; D-10 apply mapping fixes with a notice and an audit row per
  change; D-13 no website prefill; D-7, D-11, D-14, D-15 confirmed as built.
- **Assessment objectives, 2026-11-23** (owner): rule B (a passing check may satisfy its record once a person confirmed
  the population is complete); person evidence counts only once reviewed; readiness switches to objectives only after
  the independent review and the owner's sign off on the comparison report; write objectives for all remaining controls
  now, unreviewed; GOV-02 floor is one meeting a year; shared records across controls accepted; interviews name who.

### Other modules
- **Documents.** Content is HTML (TipTap v3) sanitised with DOMPurify; codes POL, STD, PRC, GDL, CHT. Approval tiers take several
  assignees (users, roles, groups): a named user must decide, a role or group is satisfied by any one member; assigning tier 1
  starts the review and notifies; the last decision publishes automatically; one rejection kills the tier and resets the
  document to draft. Acknowledgement campaigns are a different feature and are never merged with approvals.
- **Risk.** Matrix, bands and taxonomy belong to each register. A risk is `accepted` only through an approved acceptance; the
  requester can never approve; an expiry job reopens it. The scoring formula (product, additive or weighted) is per register and
  applied by a database trigger: the frontend must use `scoreOf`, never `likelihood * impact`.
- **Vendors.** Exit checks are three valued (`null` means the module that answers it is not built: never a tick, never a
  blocker). Nothing is `in_progress` until an advance happens. Tier colour is one severity ramp.
- **Identity.** Native sign in with TOTP now, behind a seam for an external provider later (ADR-0006). Admin MFA is off by default
  and switched per workspace. Signup is verify first and accepts any email domain (2026-08-13). Sharing the session between tabs
  is on, with limits, until httpOnly cookies replace it.
- **Exports.** Audit export Excel is capped at 50,000 events because larger ones outlast the edge proxy's roughly 60 second
  timeout; CSV is streamed.

### Working agreements
- The owner runs every command against the shared production host; agents hand over a sheet.
- No long test runs by agents; the owner runs anything long.
- Commits are authored `mehboob14` with no AI trailer, on GitHub and GitLab. The client's GitLab gets clean snapshot commits, not
  history, and no AI tooling folders.
- UI copy: no visible dashes, less text, popups for focused decisions, no page subtitles, consistent module headers, trust copy
  names real enforcement.
- Spec first (OpenSpec) for schema, auth, tenancy, dependency, connector, module boundary and API contract changes; docs ship with
  the code.

- **GitLab is the main version control** (owner, 2026-11-06), after malware was force pushed to every GitHub branch.
  Push with `push-gitlab.bat "message" refs/heads/feat/phase1-completion` (the local branch), never the default origin.

- **Identity (owner, 2026-11-19):** Verity will be installed on premises; Infoweise already runs its own Keycloak and
  wants one login across its products. So Keycloak is the identity hub: Verity speaks OIDC to Keycloak only, and
  customers' Entra, Okta, Google, ADFS (SAML) or Active Directory/LDAP are connected inside Keycloak. Matches ADR-0006
  (one shared realm, tenant as a claim, verified against membership on every request; authorization stays in Verity;
  native login kept as break-glass). Open details: tenant model in Keycloak, claims, provisioning owner, on-prem topology.

## Open: ask the owner, do not assume

- (2026-10-19) Who must acknowledge the code of conduct and AUP: built as every active member except guest auditors
  (memberships whose every role is engagement scoped or has a start or end date). Confirm with the client.
- (2026-10-19) Left by the second review for the owner, because each reverses an earlier deliberate call or changes
  SOC 2 for every workspace: (a) fail a risk whose next review date is set beyond its register's cadence; (b) fail a
  risk with a residual rating below inherent but no treatment decided; (c) map SOC 2 A1.2 to PE-01, and move PE-03
  into the shared library for own sites.
- (2026-10-19) SLA anchor when a severity rises: built as first detection; the alternative is the moment it rose.
- (2026-10-19) ISO 27001 on which plans: the website no longer says "every workspace"; every plan or Growth and up
  is a pricing decision.
- (2026-10-19) The crosswalk review was Verity's internal persona pass, not an independent or accredited review.
  FW-5 (a second qualified person) is still open; public copy must not cite it as independent.

1. **ISO crosswalk reviewer** (FW-5, task A5): who signs it, and when. Until then, call the mappings unreviewed.
2. **ISO titles:** ship Verity's own names (today) or short official titles after legal review. Also whether to buy ISO/IEC
   27001 and 27002 for the reviewer.
3. **Supplier inherited controls:** the Statement of Applicability has "operated by supplier"; whether to attach the supplier's
   certificate there or keep it on the vendor record is not decided.
4. **One scope or two** for SOC 2 and ISO: built as one engagement and scope per framework. Confirm before building shared boundaries.
5. **HR and device connectors** (HR-05, the EP controls): the signed connector catalogue (section 8) has no HR or MDM/EDR
   providers, and the frontend's 40 provider catalogue does not match it.
6. **The 26 controls worded for SOC 2:** neutralise their guidance with a data migration, or leave.
7. **Built in roles** from the spec (Compliance manager, Control owner, Employee, Auditor) and their object scoping: proposed,
   not decided or built. The 43 Sub-type values are a proposal, not client confirmed (D1).
8. **Questionnaires:** SIG is licensed content, CAIQ is free, Annex A and DPA can be authored (proposed reading).
9. **Marketing:** the website lists ISO 27001 as "soon". Whether and when to say it is live is the owner's call; the repo's own
   `AGENTS.md` says not to market it as live.
10. **Merging** `feat/phase1-completion` (24 commits) into `main`, and whether main stays "always deployable"; when to deploy ISO.
11. **GitLab:** whether `AGENTS.md` should also be removed from the client's repo (the AI tooling folders already were).
12. **Platform tests (C2) and module evidence** are extensions that need client agreement before they are built.
13. **AICPA text licence** and the legal read on verbatim criteria. (Same question as D-4 in the guided onboarding plan.)
14. **Guided onboarding** (2026-11-21): D-1, D-2 and D-3 DECIDED by the owner the same day (proceed and log out of
    scope work in `phase_out_1.md`; ISO without SOC 2; SOC 1 guidance only). D-6 (shared scope items, in or out per
    framework) and D-12 (Compliance Manager role, no workspace administration) also decided the same day. Still open:
    D-4, D-5, D-7 to D-11, D-13 to D-16. Original list in `docs/product/guided-onboarding/README.md`
    section 6. The blocking ones: D-1 it is outside the signed phases (scope and terms), D-2 a workspace running ISO 27001
    without SOC 2 (changes what sign up seeds), D-12 roles (no built in role but Admin can load Get Started). Also new:
    D-5 seven Openlane templates follow ISO 27001:2013 wording, D-7 country content written once and reviewed versus
    generated at run time (recommended: written once), D-10 mapping fixes that change what existing workspaces see as met.
