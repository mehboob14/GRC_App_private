# HR systems: BambooHR, Rippling, Workday, Gusto, HiBob

| | |
|---|---|
| Capabilities | hr_system |
| Delivery phase | Not in the signed catalogue. `capabilities.json` lists Workday, BambooHR, Rippling and Gusto as `not_planned`; HiBob is not listed. `docs/product/control-framework-requirements.md` open question 1 proposes a people roster import (CSV) as the HR source until an HR connector is agreed (decisions D-DEV-1, D-HR-1) |
| Auth model | Per provider: BambooHR API key (HTTP Basic) or OAuth app; Rippling API token or App Shop OAuth app; Workday Integration System User with a custom report (RaaS) or an API client (unverified: Workday login required); Gusto partner OAuth app with Gusto's review; HiBob service user (HTTP Basic) |
| Shares setup with | Nothing. People records join to the identity provider by work email |
| Go library | None official for any of the five. Plain REST (Workday SOAP only if RaaS is not used) |

Checks are written against the capability. The hr.* keys are defined in section 2 (this file is their
home); device and endpoint keys are in [mdm-and-endpoint-strategy.md](../mdm-and-endpoint-strategy.md).
People and identity keys (`people.*`) belong to the identity research: this file lists only what an HR
source contributes to them and the needs it raises.

## 1. What an HR source proves

The HR system is the record of who works for the company: when each person started and left, whether they
are an employee or a contractor, who their manager is, and their role. Many objectives test against that
list (17 objectives use `roster-of-joiners-and-leavers-with` alone, among them HR-01.B, HR-05.C, HR-05.D,
HR-06.B, HR-08.C, IAM-12.B, IAM-12.E, EP-03.C, EP-05.C and NS-11.C). Today that artifact is filled by a
person or by `people.leavers_deprovisioned`, a check about account removal rather than the list itself.

An HR source does not prove that offboarding happened, that access was removed (that needs the identity
provider and other systems), or that a background check was done unless the HR system holds screening
records, which most do not natively (Workday's `Get_Workers` has a background check response group [W1];
BambooHR, Rippling and Gusto show none in their public APIs). Training completion is reachable only where
the HR system runs the training: BambooHR's training records API [B3]; Workday Learning (unverified: login required);
HiBob's learning API only accepts records from course providers, with no documented read [H5].

## 2. Checks

### 2.1 Shared rules

- **Population** is every worker record the credential can read, active and former, employees and
  contractors. A run must show it read all of them: every page, `showInactive` or equivalent set, no
  field the check needs restricted. Otherwise `insufficient`.
- **Restricted fields.** BambooHR returns a restricted field as null and names it in `_restrictedFields`
  [B2]; HiBob silently omits fields the service user cannot see [H2]. Either case for a field a check
  needs gives `insufficient`, never a fail on the person.
- **Never filter on a restricted field.** BambooHR drops employees from a filtered or sorted result when
  the caller cannot read the field, and its total count is then understated [B2]. Collectors read
  everything and filter in Verity.
- **Period.** People records change slowly; checks run daily and keep history. Leavers are kept for 13
  months after their end date so a 12 month Type 2 window is always covered.
- **Data minimisation.** Verity keeps the fields named in each check and nothing else: no pay, no
  national identifiers, no home address, no screening report content (only date, type and cleared yes or
  no). Decision D-HR-3 covers the privacy notice and DPA impact.

### 2.2 New hr.* checks

| Check key (NEW) | Population | Predicate | pass, fail, error, insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|
| `hr.roster_exported` "People list exports from the HR system" | All worker records: active, plus anyone whose end date is in the last 13 months. Pre start records (offer accepted, not started) are listed but not counted | The read was complete, every active worker has a work email, start date, employment type and manager (people marked as top of the organisation excepted), and every worker who left in the window has an end date | pass: complete and every record has the fields. fail: records missing a field, each listed. error: credential or permission problem. insufficient: paging cut short, restricted fields, inactive workers not readable. Empty population: insufficient | daily | Dated roster: worker id, name, work email, employment type, start, end, termination type where present, manager id, department, title, status; joiners, leavers and movers since the last run | HR-05 partial: gives the leaver list and end dates offboarding is measured against; the offboarding itself is checked elsewhere. HR-06 partial: gives the joiner list onboarding is tested against. IAM-12 partial: the leaver list matches the HR tool (IAM-12.B); removal is checked by `people.leavers_deprovisioned`. HR-01 partial: the complete list of joiners the screening sample is drawn from |
| `hr.contractors_have_end_dates` "Contractors have an end date" | Active workers whose employment type is contractor (provider mapping, extendable by the tenant) | An end date is recorded and is today or later | fail: no end date, or end date passed while the record is still active. insufficient: employment type not readable. Gusto has no planned end date field, so this check needs a tenant mapped source there (section 7.3) | daily | Contractor list with start and end dates | HR-03 partial: shows each contractor has a fixed end date. Sponsor, access scope, agreements and return of equipment stay with people |
| `hr.background_checks_before_start` "Screening finished before start" | Workers whose start date is in the last 12 months; optionally moves into roles the tenant marks as sensitive | A screening record or a mapped HR field shows a completed, cleared check dated on or before the start date (or the move date) | fail: missing, not cleared, or dated after the start. insufficient: no screening source or field mapped, or the field is restricted | daily | Per joiner: start date, screening type, completion date, cleared yes or no | HR-01 partial: shows a cleared check is recorded before each start. The scope by role, legal limits per country and rechecks stay with people |
| `hr.training_current` "Security training is current" | Active workers on the run date; contractors with access per setting | A completed training of a type the tenant marks as security awareness within `refresher_interval_months` (objective parameter, 12), and for joiners within `training_due_days` (default 30) of the start date | fail: missing or older than the interval. insufficient: no training source mapped | daily | Per person: training type, completion date | HR-08 partial: shows completion against the staff list. Content, role modules and chasing overdue people stay with people |

### 2.3 What HR sources add to existing people.* checks

| Check | HR side it needs | Notes |
|---|---|---|
| `people.leavers_deprovisioned` | Leavers with end date (and termination type, for the hours limit on involuntary departures) | The HR end date is a date; the hours limit needs a time zone and, ideally, a time. Most sources give a date only: the check should start the clock at the end of the last working day in the worker's time zone (identity research decides) |
| `people.joiners_onboarded` | Joiners with start date | as defined by the identity research |

### 2.4 Needs raised for the identity research (NEED entries)

- Accounts against the roster is already defined by the identity research as NEW
  `people.accounts_match_roster` ([identity-checks.md section 2.5](identity-checks.md)); HR providers
  implement its hr_system side, and the leaver list for its `vault.leavers_removed`. No NEED raised.
- NEED identity_provider + hr_system: for each worker whose department, title or manager changed, access
  was changed or confirmed within the policy's days (HR-05.B movers, IAM-12.D; partial).
- NEED identity_provider + hr_system: each contractor's accounts are disabled by the contract end date
  unless an extension is recorded (HR-03.D; partial).
- NEED network_edge + hr_system: every member of the remote access tool is an active worker or approved
  contractor (NS-11.C; partial).
- NEED verity_tasks + hr_system: each leaver in the HR list has a closed offboarding checklist (HR-05.C;
  partial; Verity's tasks module).

## 3. What Verity collects (all providers)

| Observation | Fields (normalised) |
|---|---|
| `person.record` | provider worker id, work email, display name, status (active, leave, terminated, pre start), employment type (employee, contractor, other with the raw value), start date, end date, termination type (voluntary, involuntary, unknown), manager worker id, department, title, country, last changed time |
| `person.event` | worker id, kind (hire, termination, job change, manager change), effective date, recorded time |
| `person.training` | worker id, training type id and name, completion date |
| `person.screening` | worker id, screening type, completion date, cleared yes or no |

Matching: work email lowercased to the identity provider's user; the HR worker id is the stable key (an
email can be reused).

## 4. BambooHR

### 4.1 Connecting

| Item | Detail |
|---|---|
| Method | API key sent with HTTP Basic (key as user name, any password), against `https://{companyDomain}.bamboohr.com/api/v1/`. A key inherits the permissions of the user who created it [B1]. Alternative: OAuth through an app registered in the BambooHR Developer Portal; access tokens last an hour and a refresh token comes only with `offline_access` [B1] |
| Least privilege | Create a BambooHR user for Verity with an access level that can see only the needed fields of all employees, including former ones (custom access levels set no access, view or edit per field, per BambooHR's help centre as summarised by search; whether a level can be limited to former employees: unverified, test in a trial), then create its key. With OAuth: scopes `employee`, `employee:job`, `employee:name` [B2], plus `training` for training records [B3] |
| Plan | API access by plan not stated in the developer docs [B1]; BambooHR's help centre is summarised by search as including the API in Core, Pro and Elite (unverified: the page did not render) |
| Lockout | Repeated calls with an unknown key make the API refuse access for a while with 403 [B1] |

### 4.2 What Verity collects

| Resource | API | Fields | Paging |
|---|---|---|---|
| Employees | `GET /api/v1/employees` with `fields=` [B2] | `employeeId`, `status`, `workEmail`, `hireDate`, `terminationDate`, `jobTitleName`, `departmentName`, `reportsToId`, `employmentStatusName` (employment type) [B2] | `page[limit]` default 250, up to 2,500; cursors `page[after]`, `page[before]` or `_links.next` (`meta.page.nextCursor` is null on the last page); `filter[status]` active or inactive; the default status set is not stated, so query both [B2]. Unknown names in `fields=` are dropped silently [B2] |
| Job history (movers) | `GET /api/v1/employees/{id}/tables/jobInfo` and `/tables/employmentStatus`; `all` as the id reads every employee the caller can see [B5][B6] | jobInfo: date, department, division, jobTitle, reportsTo. employmentStatus: date, employmentStatus, termination reason and type | one call per table with `all` |
| Training | `GET /api/v1/training/record/employee/{employeeId}` [B3] | `id`, `type` (training type id), `completed` | per employee call, no paging |

Do not use `GET /api/v1/employees/directory`: it leaves out inactive and former employees and depends on
the company's directory sharing settings [B4]. Corrected: the change feed exists:
`GET /api/v1/employees/changed?since=<ISO 8601>` returns id, action and last changed time, and edits to
the job, employment status and compensation tables count as changes [B7]. Use it between full reads.

### 4.3 Check feasibility

| Check | Feasible | Notes |
|---|---|---|
| `hr.roster_exported` | yes | read both statuses; watch `_restrictedFields` |
| `hr.contractors_have_end_dates` | partial | contractor type from employment status; contract end date field is often custom (tenant maps it) |
| `hr.background_checks_before_start` | only with a mapped custom field | no standard table holds screening records [B6] |
| `hr.training_current` | yes, if the company uses BambooHR training | one call per employee |

## 5. Rippling

### 5.1 Connecting

| Item | Detail |
|---|---|
| Method | API token created in Developer, API credentials by a user allowed to manage tokens. The token carries the creator's permission profile and the scopes chosen at creation; both must allow the data [R1]. Partner route: an App Shop app installed by the customer through OAuth, with scopes and webhooks, including `employee.terminated` [R2]. Partner process: apply, build in a test company, Integration Review, at least three external installs, Launch Review, publish; no timeline given [R5]. Customers need Rippling's Identity and Access Management package for API integrations (Drata and Secureframe call it App Management) [R5] |
| Least privilege | scope `workers.read` [R3]; expanding employment type, department or manager may need further read scopes: the scope list has `employment-types.read`, `departments.read`, `users.read` [R6], but no page ties an `expand` to a scope (unverified) |
| Token life | Revoked automatically if its owner is terminated or if it is unused for more than 30 days [R1]. Daily runs keep it alive; the owner leaving kills it, so the customer should create it from a long lived admin account. No service accounts are documented, and a token cannot move to another owner [R1] |
| Plan | Some APIs need a separate entitlement; ask the Rippling account manager [R1] |

### 5.2 What Verity collects

| Resource | API | Fields | Paging |
|---|---|---|---|
| Workers | `GET https://rest.ripplingapis.com/workers/` with `Authorization: Bearer` [R1][R7] | `id`, `user_id`, `work_email`, `status` (INIT, HIRED, ACCEPTED, ACTIVE, TERMINATED), `start_date`, `end_date`, `termination_details` (type VOLUNTARY, INVOLUNTARY, RETIREMENT, DEATH, ABANDONMENT, OFFER_DECLINED, RESCIND or RENEGE, and reason; corrected from two values), `employment_type_id` (with `expand=employment_type`, `type` CONTRACTOR or EMPLOYEE), `manager_id`, `department_id`, `title`, `title_effective_date`, `country` | `limit` 1 to 100 (default 50), `cursor`, `next_link`; filters `status`, `work_email`, `user_id`, `created_at`, `updated_at` [R3] |
| Worker changes | `GET /worker-changes/` polled by `applied_on`; scope `worker-changes.read`, the Rippling API SKU and a beta entitlement; includes `OFFBOARD` and `SCHEDULED_OFFBOARD`; unreadable fields show as REDACTED [R4] | changed fields and dates | |

Terminated workers: `TERMINATED` is a status and filterable; whether the default list includes them is
not stated [R3]: query each status explicitly.

### 5.3 Check feasibility

| Check | Feasible | Notes |
|---|---|---|
| `hr.roster_exported` | yes | |
| `hr.contractors_have_end_dates` | yes | `employment_type` CONTRACTOR with `end_date` |
| `hr.background_checks_before_start` | no: not in the public API index [R2] | |
| `hr.training_current` | no: not in the public API index [R2]; Secureframe also says its Rippling sync does not pull training | |

## 6. Workday

**Verification status.** Most of Workday's documentation is behind the Workday Community login. The
public `Get_Workers` web service reference was read [W1]; the rows it confirms say so. Everything else in
this section is unverified (login required) and must be confirmed with a customer's Workday team.

| Item | Detail (unverified) |
|---|---|
| Method, recommended | A custom report built by the customer's Workday team with exactly the fields Verity needs, exposed as a web service (Report as a Service, JSON), run by an Integration System User. The customer controls what leaves Workday, which is least privilege by construction |
| Alternative | Workday Web Services `Get_Workers` (Human Resources service, SOAP), confirmed [W1]: flags exclude inactive workers, employees or contingent workers, and response groups include employment, organisations, management chain and contracts for terminated workers. The REST API with an API client (OAuth 2.0 with refresh tokens) stays unverified |
| Permissions | The Integration System User sits in an integration system security group with view access to the worker data domains the report uses (`Get_Workers` names Worker Data: Current Staffing Information [W1]; public worker reports and termination data domains: unverified) |
| Workers | Employees and contingent workers are both workers [W1]; the report must include both and terminated workers within 13 months. Excluding inactive workers drops ended contingent contracts too [W1] |
| Background checks | `Get_Workers` has a background check response group [W1]; usable only if the customer runs checks in Workday and adds them to the report |
| Training | Workday Learning, if licensed (unverified: login required) |

Check feasibility: `hr.roster_exported` yes (by report design), `hr.contractors_have_end_dates` yes if the
contract end date is in the report, the other two only if the customer uses the matching Workday modules.

## 7. Gusto

### 7.1 Connecting

| Item | Detail |
|---|---|
| Method | OAuth app integration. Gusto assigns scopes during its review of the app according to the use case; scopes are tested in Gusto's demo environment and enforced in production after approval; scope changes go through Gusto's developer support [G1]. Verity must apply as a Gusto app partner before any customer can connect: production needs a pre approval and a security review, and production keys come after QA [G4] (lead time unverified: not published) |
| Least privilege | `employees:read` [G2]; `contractors:read` [G3]. Do not request `compensations:read` (pay fields) [G2] |
| Header | `Authorization: Bearer <token>` and `X-Gusto-API-Version` [G2]; demo host `api.gusto-demo.com` |

### 7.2 What Verity collects

| Resource | API | Fields | Paging |
|---|---|---|---|
| Employees | `GET /v1/companies/{company_id}/employees` (returns onboarding, active and terminated employees) [G2] | `uuid`, `work_email`, `terminated`, `terminations[].effective_date`, `onboarded`, `onboarding_status`, `jobs[].title`, `jobs[].hire_date`, `department`, `manager_uuid`, `current_employment_status` | `page`, `per` (Gusto's general default is 25; this page gives none, and without `page` all records may return at once); `terminated` filter (terminated or scheduled to be) [G2]. Note: `current_employment_status` is full or part time, not employee or contractor |
| Contractors | `GET /v1/companies/{company_uuid}/contractors`, active and inactive [G3] | `uuid`, `type` (Individual or Business), `is_active`, `start_date`, `dismissal_date`, `email`, `work_email`, `department` | as employees |

### 7.3 Check feasibility

`hr.roster_exported` yes (employees and contractors read separately). `hr.contractors_have_end_dates`:
corrected to **no**. Gusto contractors carry only `dismissal_date`, set when the engagement ends, and no
planned end date [G3], so every active contractor would fail. On Gusto this check needs a tenant mapped
source for contract end dates or stays with people. Screening and training: not available (unverified:
not checked).

## 8. HiBob

### 8.1 Connecting

| Item | Detail |
|---|---|
| Method | A service user created in Bob's Service Users section (by a Bob admin); its id and token go in the Authorization header as HTTP Basic (`id:token` in base64) [H3]. The token can be copied only when it is generated [H1] |
| Least privilege | A service user has no access by default. Create a permission group for it with: the People features needed, View on the needed People's data categories, and access rights covering everyone, including former employees (the default covers active employees only; Bob's page states the default two ways, so set it explicitly) [H1][H2] |
| Base URL | `https://api.hibob.com/v1` (sandbox `https://api.sandbox.hibob.com/v1`) [H2] |

### 8.2 What Verity collects

| Resource | API | Fields | Paging and limits |
|---|---|---|---|
| People | `POST /v1/people/search` with `showInactive: true` (default false) and an explicit `fields` list (up to 400) [H2]. No paging: one call returns everyone. Unreadable or invalid fields are left out with a 200, so compare the response to the request [H2] | `root.id`, `root.email`, `work.startDate`, `internal.status`, `internal.lifecycleStatus`, `work.reportsTo`, `work.department`, `work.title` [H2]; `payroll.employment.type` (seen only in an example on that page: unverified); termination date read field not found (unverified) | Corrected: people search allows 50 calls a minute, with `X-RateLimit-*` headers; more than 50 authentication failures in 10 seconds block the IP for 5 minutes, so never retry 401 or 403 [H4] |
| Work history (movers) | `GET /v1/bulk/people/work` (cursor paged, up to 200 ids) and `GET /v1/bulk/people/employment`; full history needs the View history permission on Work [H6] | | |

### 8.3 Check feasibility

`hr.roster_exported` yes, provided `showInactive` and the access rights include former employees;
`hr.contractors_have_end_dates` yes if contract end is a field the tenant maps; training: Bob's learning
API has no documented read [H5]; screening unverified (not checked).

## 9. Fallback: people roster import

For customers without a supported HR system, the proposal in open question 1 stands: a CSV roster import
(worker id, email, type, start, end, manager) acts as the hr_system provider `roster_import`. Its rows are
a person's evidence: `hr.roster_exported` reads them as `insufficient` for completeness (a file cannot
prove it is the whole list) and the roster artifact keeps its person source. Decision D-HR-1.

## 10. Artifacts and objectives it fills

| Artifact key | Objective codes | Control | Change |
|---|---|---|---|
| `roster-of-joiners-and-leavers-with` | HR-01.B, HR-05.C, HR-05.D, HR-06.B, HR-08.C, IAM-12.B, IAM-12.E, EP-03.C, EP-05.C, NS-11.C (and seven others) | HR-01, HR-05, HR-06, HR-08, IAM-12, EP-03, EP-05, NS-11 | person + `people.leavers_deprovisioned` -> person + `hr.roster_exported` (fills full: it is the roster); keep `people.leavers_deprovisioned` on the removal records artifact instead |
| `contractor-register-with-start-and-end` | HR-03.B, HR-03.C, HR-03.D | HR-03 | person -> person + `hr.contractors_have_end_dates` (partial: access and sponsor are not in HR) |
| `completed-background-checks-for-a-sample` | HR-01.B to HR-01.E | HR-01 | person -> person + `hr.background_checks_before_start` (partial, only with a screening source) |
| `completion-records-for-all-staff` | HR-08.B, HR-08.C, HR-06.E, HR-03.C | HR-08, HR-06, HR-03 | person -> person + `hr.training_current` (partial, only with a training source) |
| `removal-records-for-a-sample-of` | IAM-12.B, IAM-12.C | IAM-12 | unchanged key (`people.leavers_deprovisioned`), now with an HR provider |

## 11. Framework reach

HR-01: SOC 2 CC1.1, CC1.4; ISO 27001:2022 A.6.1. HR-03: CC6.2, CC9.2; A.5.11, A.8.30. HR-05: CC6.2,
CC6.3; A.5.11, A.6.5. HR-06: CC1.4, CC6.2; A.5.4. HR-08: CC1.4, CC2.2; clauses 7.2 and 7.3, A.5.17, A.6.3,
A.8.7. IAM-12: CC6.2, CC6.3; A.5.16, A.5.18. All through partial mappings.

## 12. Limits and false assurance traps

- **The HR list is only as complete as HR keeps it.** Contractors hired by a team lead and paid through
  accounts payable often never appear. `hr.roster_exported` passing says the HR list is well formed, not
  that every worker is in it; the identity reconciliation NEED covers the gap.
- **End date is not last access.** HR records the contractual end; garden leave and early access cuts
  differ. Checks use the end date as the policy start point and say so.
- **Back dated terminations** are common: a leaver entered a week late looks on time if Verity only reads
  the end date. Keep the first time Verity saw the termination and report both.
- **Rehires** reuse emails. Key on worker id.
- **Restricted and omitted fields** look like missing data. Treat as `insufficient`, never `fail`.

## 13. Product and UI

Connect forms: BambooHR company domain and API key (or OAuth); Rippling token; HiBob service user id and
token; Gusto OAuth button (after partner approval); Workday tenant URL, report URL and the integration
user's credentials. Settings: which employment types count as contractor, which training type is security
awareness, the screening field, the HR to identity match rule. Health: credential invalid, inactive
workers not readable (`insufficient` with the fix), restricted fields listed by name. In product guide:
yes for each provider (the least privilege setup is the hard part).

## 14. Implementation notes

- One REST client per provider on the shared runtime; cursor paging to the end, otherwise `truncated`.
- Store only the normalised fields; drop the raw payload after normalisation except a field allow list
  kept for audit retrace.
- Fixtures per provider: an active employee, a contractor with and without end date, a leaver this month,
  a leaver 14 months ago, a rehire, a restricted field.
- Test accounts: Gusto's demo environment [G1], HiBob's sandbox host [H2], a Rippling test company for
  partners [R5]; BambooHR trial (unverified: not checked); Workday only through a customer or partner tenant.

## 15. How comparable platforms do it, and aggregators

| Platform | What was found |
|---|---|
| Vanta | BambooHR by OAuth with a signed in BambooHR user (view only custom level or full admin), advised to be a non employee user (search summary of Vanta's page: unverified). Uses Merge for at least one HR system (7shifts) [C1] |
| Drata | Some HR connections run through Merge and may ask for a payroll permission Drata does not use; reads name, email, employment status, start and separation dates; background checks come from a separate Checkr integration; Rippling needs the App Management package [C2] |
| Secureframe | Lists Gusto, BambooHR and Rippling; Rippling needs App Management and does not sync training (search summaries: unverified); no Merge or Finch mention found |
| Sprinto | Not checked (unverified) |

No Finch use was found on Vanta, Drata or Secureframe pages. An aggregator would replace five integrations
with one contract and one data processor; that trade is decision D-HR-2.

## 16. Sources

- [B1] BambooHR getting started (auth, base URL, permissions, lockout): https://documentation.bamboohr.com/docs/getting-started
- [B2] BambooHR List Employees: https://documentation.bamboohr.com/reference/list-employees
- [B3] BambooHR list employee trainings: https://documentation.bamboohr.com/reference/list-employee-trainings
- [B4] BambooHR employee directory: https://documentation.bamboohr.com/reference/get-employees-directory
- [B5] BambooHR get employee table data: https://documentation.bamboohr.com/reference/get-employee-table-data
- [B6] BambooHR table and field names: https://documentation.bamboohr.com/docs/table-name-fields
- [B7] BambooHR changed employee ids: https://documentation.bamboohr.com/reference/get-changed-employee-ids
- [R1] Rippling API tokens and permissions: https://developer.rippling.com/documentation/rest-api/essentials/api-tokens.md
- [R2] Rippling developer docs index (App Shop OAuth, scopes, webhooks): https://developer.rippling.com/llms.txt
- [R3] Rippling List workers: https://developer.rippling.com/documentation/rest-api/reference/list-workers.md
- [R4] Rippling worker changes guide: https://developer.rippling.com/documentation/rest-api/guides/worker-changes.md
- [R5] Rippling App Shop partner process: https://developer.rippling.com/documentation/developer-portal/getting-started/process.md
- [R6] Rippling permissions and scopes: https://developer.rippling.com/documentation/rest-api/essentials/permissions.md
- [R7] Rippling HRIS getting started (base URL): https://developer.rippling.com/documentation/rest-api/guides/hris-getting-started.md
- [G1] Gusto API scopes: https://docs.gusto.com/app-integrations/docs/scopes
- [G2] Gusto get employees: https://docs.gusto.com/app-integrations/reference/get-v1-companies-company_id-employees
- [G3] Gusto get contractors: https://docs.gusto.com/app-integrations/reference/get-v1-companies-company_id-contractors
- [G4] Gusto app integrations introduction (production approval): https://docs.gusto.com/app-integrations/docs/introduction
- [H1] HiBob API service users: https://apidocs.hibob.com/docs/api-service-users
- [H2] HiBob search people: https://apidocs.hibob.com/reference/post_people-search
- [H3] HiBob authorization: https://apidocs.hibob.com/reference/authorization
- [H4] HiBob rate limiting: https://apidocs.hibob.com/reference/rate-limiting
- [H5] HiBob learning LMS API: https://apidocs.hibob.com/docs/explore-learning-lms-api
- [H6] HiBob bulk work history: https://apidocs.hibob.com/reference/get_bulk-people-work
- [W1] Workday Get_Workers (Human Resources v45.0, public): https://community.workday.com/sites/default/files/file-hosting/productionapi/Human_Resources/v45.0/Get_Workers.html
- [C1] Vanta, connecting 7shifts through Merge: https://help.vanta.com/en/articles/11898664-connecting-vanta-7shifts-merge ; BambooHR page (did not render): https://help.vanta.com/en/articles/11345684-connecting-vanta-bamboo-hr
- [C2] Drata, connect your HRIS: https://help.drata.com/en/articles/8699680-connect-your-hris-to-drata
- Workday RaaS, Integration System User and REST client setup: Workday Community login required, not read
