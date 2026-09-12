# Week 5 — third-party risk: completion note

Written at close, 2026-09-10. What shipped, what knowingly did not, and what the next person
needs to know before they touch this module.

## What shipped

Sections 0 through 6 of `tasks.md`, in six commits:

| Commit | Section |
|---|---|
| `3d05294` | 0 — the build reference (§1 of `design.md`, all 26 ER tables verbatim plus the deviation register) |
| `3e2becc` | 1 — the register foundation |
| `c1319d4` | 2 — inherent tiering and the twelve-stage lifecycle |
| `02de736` | 3 — the questionnaire bank, the vendor portal, residual scoring and findings |
| `8b3b65a` | 4 — the approval gate, the paperwork, intake and the evidenced exit |
| `abb2e00` | 5 — the interface |

Twenty-eight tables (twenty-five tenant-owned, three on the global content plane), 35 authenticated
routes plus four unauthenticated portal routes, and a frontend feature of 23 components over
the usual three module files.

## The one place this change falls short of the contract

**Finding → risk-register promotion is not built, and spec ¶85 and the ¶109 exit criterion are
therefore not fully satisfied.**

This was declared in the proposal before a line was written and it is still true at close. It is a
sequencing gap, not a design one: `modules/risk/` is an empty stub with no tables in any migration
and a `.gitkeep` for a frontend feature. The seam is designed on both sides and is in the schema —
`risks.risk_source` already reserves the value `vendor_finding`, and `vendor_findings` ships a
nullable `promoted_risk_id` with **no foreign key and no promotion action**.

What that means concretely, so nobody builds on sand:

- `FindingOut.promoted_risk_id` is **permanently `null`** in every response the module can produce
  today. There is no code path that writes it. Do not build UI, filters, counts or reports on it.
- There is no "promote to risk" control anywhere in the interface, deliberately. A button that
  writes nothing is worse than an absent one, because it teaches people the link exists.
- A vendor finding that a reviewer decides to live with is recorded as **accepted with a
  time-boxed date and a rationale** on the finding itself. That is a complete decision inside this
  module, and it is what an auditor is shown today. It is *not* a register entry, and the two
  should not be confused when the risk slice lands: accepted findings are not automatically risks.

**When `modules/risk/` ships**, three things close the gap: add the real FK on
`vendor_findings.promoted_risk_id`; add a promotion action in the vendors service that writes a
risk with `risk_source = 'vendor_finding'` inside the same transaction as the audit row; and
surface it on the findings panel beside Accept and Close. The exit-check machinery needs no change
— `lifecycle.py` already models a check whose answering module does not exist as three-valued, so
a `risk.promoted` check can be added as `satisfied=None` today and start answering the day the
tables arrive, without a rule changing.

## Other things built but not fed

None of these is a shortfall against the spec; they are all scope that was confirmed and shipped
without a data source. Each says so on screen rather than rendering an empty table, because on a
monitoring surface "watching and found nothing" and "not watching" look identical and mean
opposite things.

- **`vendor_scorecards`, `vendor_signals`, `vendor_discovered_apps`, Slack alert delivery.** Built,
  migrated, surfaced. Nothing feeds them until Phase 2, and the scorecard providers are not in the
  connector catalogue in any planned phase.
- **`vendor_slas`.** The table is modelled. No route exposes it, so the contracts panel shows only
  the contractual windows that do arrive — the breach-notification hours and the auto-renewal
  notice deadline — and says plainly that per-metric service levels have no endpoint yet.
- **Roster removal.** `POST /vendors/roster` assigns and is idempotent; nothing unassigns. The
  roster page offers an add-only control rather than removable chips, because a remove button that
  silently does nothing is worse than no remove button.
- **Stage notifications.** There is no notification route for vendor stages, so "let them know" on
  the gate handoff and "request a renewal" on an expiring document open the reader's own mail
  client. Neither pretends Verity sent anything.

## What the interface found in the backend

Building section 5 against the real API exposed seven defects that no backend test had caught,
each fixed at the source rather than worked around. They are listed in full in `tasks.md` under
section 5. The one worth repeating here is the class of bug, not the instance:

**Three GET routes were dead on arrival.** `GET /vendors/findings`, `/intake` and `/roster` were
declared after `GET /{vendor_id}`, so the path parameter captured them and they answered 422 —
never data, never a 404. Nothing caught it because all three vendor "integration" tests drive
`vendor_service` directly and make zero HTTP calls: `grep -c "api/v1/vendors"` returns 0 in all
three files. A module can have a green suite and an unreachable third of its read surface.
`backend/tests/unit/test_route_shadowing.py` now proves the ordering rule for every router in the
application and guards itself against passing vacuously.

The lesson for the next module: **service-level integration tests do not test the API.** At least
one test per module has to go through the app. This module now has one —
`backend/tests/integration/test_vendor_routes.py` — deliberately shallow and wide: it proves every
read route resolves to its own handler and returns its own shape, that an unauthenticated caller
gets 401 on each of them (a shadowed route inherits the *other* route's guard, so deny-by-default
has to be proved per path), and it walks the smallest write path that reaches the approval gate.
Depth stays in the service suites; reachability lives there.

## How this was verified

- `make check` clean: ruff format, ruff check, mypy strict over 213 files, import-linter 17/17.
- `tests/isolation/` — 55 passed. RLS coverage is systemic: `test_rls_coverage.py` auto-discovers
  every class mixing in `TenantScoped` and demands enabled + forced RLS and at least one policy, so
  all twenty-five tenant-owned vendor tables are covered by construction rather than by a list
  somebody has to maintain.
- The Week-5 review script walked end to end against a live backend and a live browser, on real
  Postgres with RLS on. See the walkthrough section of this note.

## Walkthrough, run against a live stack

Every step below was executed, not reasoned about.

1. **Add a vendor.** Three created through `POST /vendors`, each with its first engagement.
2. **Tier it.** One scored 80 → critical, one 13.75 → low. The low-tier engagement's stage plan
   came back with `diligence`, `questionnaire`, `scoring` and `findings` marked skipped and
   carrying `skipped_by_policy = "low tier"`; the gate was **not** skipped, which is the rule the
   whole tier matrix depends on.
3. **Issue a questionnaire.** 59 questions in scope, a portal URL returned once.
4. **Answer it as the vendor.** Opened the portal link in a browser with no session, answered a
   question, watched the progress go to 1 of 59 and the notes field appear. No account, no
   sign-in, no app shell.
5. **Log a finding.** Recording a SOC 2 review with a qualified opinion raised a critical finding
   automatically, which then appeared in the cross-vendor findings queue named against its vendor.
6. **The approval gate.** Advanced a low-tier engagement to the gate: intake → tiering →
   **contracting**, skipping four stages in one move, which is the proportionality being visible
   rather than implied. At the gate the only member of the tenant was refused as an approver with
   the reason *"business owner of this vendor"*, and the interface greyed them out and said so
   before any rationale could be typed. Deciding required a second person — which is the point.

## Two things a reader will get wrong

Recorded here as well as in `docs/architecture/data-model.md`, because they cost real time:

1. **A freshly tiered engagement has no stage marked `in_progress`.** All twelve rows are written
   `not_started` and one only enters `in_progress` when the stage before it is completed. "Where
   the work is" is the first row that is neither complete nor skipped.
2. **`approval.decided` is a blocker that only its own decision clears.** Gate the decision control
   on the raw blocker list and the gate can never be passed.
