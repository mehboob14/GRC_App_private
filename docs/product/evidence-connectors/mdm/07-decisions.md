# 7. Owner decisions for device evidence

Round 2 decisions, consolidated from the research files (D-DEV-14 to 17 in apple-mdms, D-ACG-1 to 3 in
android-chromeos-google, D-MKT-1 to 5 in market-and-audit) and from the process and checks. Round 1 decisions
D-DEV-1 to D-DEV-13 and D-HR-1 to 4 stay in `../mdm-and-endpoint-strategy.md` section 9; where round 2
changes one, the row says so. Nothing here is decided yet. Each decision is to be asked as a clickable round,
recommended option first.

## 7.1 The gate

| # | Decision | Options | Recommended |
|---|---|---|---|
| D-DEV-1 (round 1) | Bring device management into scope with the client | keep manual; extension with the client; Phase 3 | extension, sequenced as D-MDM-1 |

## 7.2 Round 2 decisions

| # | Decision | Options | Recommended | Source |
|---|---|---|---|---|
| D-MDM-1 | Wave 1 providers and order | round 1 order (Intune, Google, Jamf, Iru); add JumpCloud; other | Intune with Defender, Google devices, Jamf Pro, Iru, JumpCloud, with Apple Business as the purchase source | market 9 item 1 (D-MKT-1); replaces D-DEV-2 |
| D-MDM-2 | Phone and tablet checks | none; company owned phones only; all phones | company owned phones only; personal phones evidenced by access rules | market (D-MKT-2) |
| D-MDM-3 | Serial number on personal devices | never stored; tenant keyed hash for matching | never stored, until a matching need is shown | market (D-MKT-3) |
| D-MDM-4 | Personal devices and unknown ownership | personal in scope per tenant setting; unknown treated as personal or company | per tenant setting, default in scope when they reach company data; unknown treated as personal until classified | D-DEV-7 refined; D-MKT-4 |
| D-MDM-5 | Device type in Assets | add (migration, RLS unchanged, CHECK constraint); keep devices outside Assets | add | D-DEV-6 restated: LM-01.C and EP-08.B need it |
| D-MDM-6 | Per resource exception waiver in the outcome engine | yes (05 5.8); no (exceptions only as separate evidence, a single excepted laptop keeps EP-02.B in deviation) | yes | 05 5.8 |
| D-MDM-7 | Content changes CC1 to CC7 (04 4.7), including new objective EP-03.F and three new artifacts | accept after D2; accept some; reject | accept after D2 | 04 4.7 |
| D-MDM-8 | Default settings (05 5.14) | as drafted; amend | confirm or amend | D-DEV-8 extended |
| D-MDM-9 | Mobile screen lock default | 2 minutes (CIS 4.3); 5 minutes; same as computers (15) | 2 minutes, editable per tenant | market (D-MKT-5) |
| D-MDM-10 | Android "current" | patch age default 90 days; Verity keeps a reviewed vendor support table (reviewed quarterly); no table (version and patch age only) | 90 days and a reviewed table | android (D-ACG-1, D-ACG-2) |
| D-MDM-11 | Zero touch, which has no read only credential | refuse and accept a CSV purchase list; accept the full scope credential | refuse; CSV purchase list import | android (D-ACG-3) |
| D-MDM-12 | Credentials that can reach secrets on some routes (Fleet Observer, Workspace ONE per device security call, which is the only source of its escrow and passcode flags, ManageEngine encryption read, JumpCloud, Google mobile privilege) | refuse; accept with endpoint and field allowlists plus an admin warning; require the narrowest option where one exists | accept with allowlists and warning; require the narrower option where it exists (Fleet Premium endpoint list, SimpleMDM without Device Secrets) | xplat-a, xplat-b, apple-mdms |
| D-MDM-13 | Customer privacy pack (field list per provider and ownership, worker notice template, DPIA inputs, works council note) | build; skip | build, small | market 9 item 12 |
| D-MDM-14 | Hexnode, whose only API key has admin power | refuse until a scoped key exists; accept as an exception | refuse; attestation meanwhile | xplat-a C |
| D-MDM-15 | Apple Business built in device management as an Apple source with no vendor in between | plan for wave 2; ignore | plan for wave 2 once Apple documents the permission for its device routes | apple 4.2 |
| D-MDM-16 | Source of the permitted software list (EP-03.E) | a list kept in Verity; the MDM's managed catalogue counts as the list; both | both: the catalogue counts, plus an allow list in Verity for the rest | 04 4.2 |
| D-MDM-17 | Mosyle | wait for a public reference and a token only method; build from community knowledge; never | wait; attestation meanwhile | apple-mdms (D-DEV-15, D-DEV-16) |
| D-MDM-18 | Jamf Compliance Benchmarks | read as secondary evidence (integration renewed every six months); ignore | read when the customer already uses them | apple-mdms (D-DEV-14) |
| D-MDM-19 | Intune Data Warehouse history at connect (60 days of compliance, management state and OS, no encryption) | use as provider history for the weeks before Verity connected, labelled as such; ignore | use, labelled; encryption before connection stays people evidence | microsoft 3, 5 |
| D-MDM-20 | Customers without any MDM | attestation plus agent sources the customer already has (Endpoint Verification, Device Trust); Verity hosts Fleet; Verity builds its own agent | attestation and existing agent sources; keep round 1's "no Verity agent now" with its demand trigger | xplat-b 8; D-DEV-3 restated |

## 7.3 Decisions answered elsewhere that this plan relies on

| Decision | State | Where |
|---|---|---|
| Rule B (a passing check may satisfy its artifact once a person confirmed the population) | decided 2026-11-23 | `../01-evidence-model.md` 1.2 |
| G1 refinement (only `full` fills satisfy alone) | open | `../08-owner-decisions.md` |
| ADR-0016 Go collectors beside the Python core | proposed | `docs/adr/0016-go-collectors-beside-the-python-core.md` |
