# Verity Design System v1.0

Extracted from Figma `MaJ0JAker7oSIiAK6HqgO7`, pages "DS · Overview" (60:4869), "DS · 1 Color"
(60:4870), "DS · 2 Type" (60:4871), "DS · 3 Space & Elevation" (60:4872), "DS · 4 Buttons & Forms"
(60:4873), "DS · 5 Status & Data" (60:4874), "DS · 6 Overlays & Feedback" (60:4875). The authority
on each page is the board labelled **VERITY DESIGN SYSTEM · V1.0**. Each page also carries an older
unlabelled summary frame (`bg` / `accent #1C4E80` / `pass`/`fail` naming — the set currently in
`frontend/src/styles/tokens.css`); that set is **superseded** by this document.

This document is the standard every screen is built against. Components consume **semantic tokens
only — no raw hex in product code**.

> System stats from the file: 22 screens · 84 components · Light + dark · WCAG 2.x AA.
> Counts in this doc are from re-reading the v1.0 boards: **44 semantic colour tokens + 39
> primitives** and **15 core text styles + 4 specialised** (code-chip, 3 numerals). The legacy
> summary frames claim "57 colour tokens / 15 text styles"; the 15 matches the core type ramp, the
> 57 does not correspond to any enumeration on either board (the legacy frame's own list has 39).
> Do not pad to 57 — the tables below are the complete v1.0 sets as drawn.

---

## 1. Design principles

| # | Principle | Rule |
|---|---|---|
| 01 | Evidence over decoration | Every pixel communicates state, enables action, or provides structure. No shadows on static content. |
| 02 | Same thing, same look | A code chip, a status pill, an owner cell — identical anatomy on every screen. Users build reflexes. |
| 03 | Density with hierarchy | More rows, not bigger cards. Density comes from vertical rhythm and weight contrast, never from shrinking type. |
| 04 | Status is a language | Green, red, amber, indigo, gray are vocabulary — never decorative, never used alone. |
| 05 | Shallow depth | List → drawer → page. Two clicks to any detail. Overlays preview; pages own. |
| 06 | Predictable machinery | Filters, bulk bars, sort and search behave identically across all nine table screens. |
| 07 | Guard dangerous paths | Destructive and audit-relevant actions name their consequence before they run. |
| 08 | Feedback in 100ms | Every interaction acknowledges instantly, even when the work is slow. |
| 09 | Keyboard first-class | ⌘K, full tab traversal, visible focus, Esc always retreats. |

**Compact vs. whitespace** — Compact (4–8px) inside repeating data · comfortable (16–24px) between
unrelated regions · generous (32–48px) only on low-density focal screens. Never add whitespace
inside a data region to breathe — add it between regions to group.

**Overview notes** (from the Overview page; token names shown there are v0 — v1.0 equivalents in
brackets):

- **Hierarchy is tokens, never opacity.** Use text [text-primary], text-muted [text-secondary],
  text-faint. Opacity multiplies against whatever is behind it, so the same value reads differently
  on a card, a row and a banner.
- **Every surface has a paired foreground.** Each -bg has an -fg. If a pair is missing, that is
  where hand-typed hex accumulates — it is how 782 literals got into this product.
- **Colour is for status, nothing else.** People use the neutral identity ramp. Frameworks, types
  and taxonomies are neutral. A person is not a status.
- **11px floor, 4px grid.** Nothing functional below 11px. Every line height lands on 4.
- **States are designed, not retrofitted.** Empty, loading, error and success ship with the screen.
  The first version of this product had none of the four.
- **Neutral elevation.** Shadows are grey. A shadow tinted with the accent is the default look of
  generated UI.

---

## 2. Colour

Primitives, semantic tokens, status triads, and dark mode. Components consume semantic tokens only.

### 2.1 Primitives — the only raw hex in the system (39)

Everything else aliases these.

| Ramp | Step | Hex |
|---|---|---|
| Gray | 900 | `#101828` |
| Gray | 700 | `#344054` |
| Gray | 600 | `#475467` |
| Gray | 500 (new) | `#667085` |
| Gray | 400 | `#98A2B3` |
| Gray | 300 | `#D0D5DD` |
| Gray | 200 | `#E4E7EC` |
| Gray | 100 | `#F2F4F7` |
| Gray | 50 | `#F4F5F7` |
| Gray | 25 | `#FBFCFD` |
| Gray | canvas | `#E7E9EE` |
| Gray | white | `#FFFFFF` |
| Sky | 800 | `#075985` |
| Sky | 700 | `#0369A1` |
| Sky | 600 | `#0284C7` |
| Sky | 200 | `#CBE3F3` |
| Sky | 100 | `#EAF4FB` |
| Green | 700 | `#08794F` |
| Green | 600 | `#059669` |
| Green | 200 | `#C7E9D9` |
| Green | 100 | `#E7F5EF` |
| Rose | 800 | `#9B1C34` |
| Rose | 700 | `#C01741` |
| Rose | 600 | `#E11D48` |
| Rose | 200 | `#F6CFD8` |
| Rose | 100 | `#FDEEF1` |
| Crimson | 700 | `#B42318` |
| Crimson | 100 | `#FBEDED` |
| Amber | 800 | `#8A4B08` |
| Amber | 700 | `#B25E09` |
| Amber | 600 | `#D97706` |
| Amber | 200 | `#F0D9B4` |
| Amber | 100 | `#FBF1E4` |
| Indigo | 700 | `#4A5AA0` |
| Indigo | 600 | `#5B72B3` |
| Indigo | 100 | `#EEF1FA` |
| Slate | 700 | `#566072` |
| Slate | 600 | `#64748B` |
| Slate | 100 | `#F0F2F5` |

### 2.2 Semantic — surfaces & borders

What components actually reference.

| Token | Light | Dark | Usage |
|---|---|---|---|
| `surface-canvas` | `#E7E9EE` | `#0A0E16` | Outside the app frame only |
| `surface-page` | `#F4F5F7` | `#0F1622` | App / page background |
| `surface-primary` | `#FFFFFF` | `#151D2B` | Cards, tables, sidebar, topbar, overlays |
| `surface-sunken` | `#FBFCFD` | `#1A2434` | Table headers, wells, kanban columns, segmented tracks |
| `surface-hover` | `#F2F4F7` | — not specified | Row hover, nav hover |
| `surface-inverse` | `#101828` | — not specified | Bulk bar, tooltips, toasts |
| `border-default` | `#E4E7EC` | `#28344B` | All structural borders and dividers |
| `border-strong` | `#D0D5DD` | `#36455F` | Checkbox resting, dashed add-affordances |

### 2.3 Semantic — text

Contrast measured on white. text-faint may never be the only carrier of information (F2).

| Token | Light | Dark | Contrast (light) | Usage |
|---|---|---|---|---|
| `text-primary` | `#101828` | `#E7EBF3` | 17.6:1 | Headings, primary cells, values |
| `text-secondary` | `#475467` | `#9AA7BD` | 7.4:1 | Body, descriptions |
| `text-subtle` | `#667085` | — not specified | 4.8:1 | Timestamps, helper text, captions — new token (F2) |
| `text-faint` | `#98A2B3` | `#697892` | 2.8:1 ✗ | Decorative only: placeholders, disabled |
| `text-link` | `#0369A1` | — not specified | 5.4:1 | All text links (F1) |
| `text-inverse` | `#FFFFFF` | — not specified | — | On inverse / filled surfaces |

### 2.4 Semantic — actions

F1: interactive fills and text links use sky-700; sky-600 is the accent for selected states, icons,
focus, charts.

| Token | Light | Dark | Usage |
|---|---|---|---|
| `action-primary` | `#0369A1` | — not specified | Filled primary buttons · hover `#075985` |
| `action-accent` | `#0284C7` | `#38B6F0` | Selected states, active tab, focus ring, chart lines, code chips |
| `action-accent-tint` | `#EAF4FB` | `#122A3D` | Selected row / nav background, active chips |
| `action-accent-border` | `#CBE3F3` | — not specified | Border of active chips and facets |
| `action-danger` | `#C01741` | — not specified | Destructive fills · hover `#9B1C34` |
| `action-danger-tint` | `#FDEEF1` | — not specified | Destructive secondary hover background |

Hover values are part of the spec: `action-primary-hover #075985`, `action-danger-hover #9B1C34`.

### 2.5 Status triads (6 × base/text/bg = 18)

Each family ships base (dots, bars) · text (words on tint, ≥4.5:1) · bg (tint). Words <18px always
use `-text`, never `-base`.

| Family | base (light) | text (light) | bg (light) | base (dark) | bg (dark) |
|---|---|---|---|---|---|
| `status-success` | `#059669` | `#08794F` | `#E7F5EF` | `#34C88A` | `#0F2E22` |
| `status-danger` | `#E11D48` | `#C01741` | `#FDEEF1` | `#F2566E` | `#301620` |
| `status-warning` | `#D97706` | `#B25E09` | `#FBF1E4` | `#E9A23B` | `#2E230F` |
| `status-progress` | `#0284C7` | `#0369A1` | `#EAF4FB` | — not specified | — not specified |
| `status-pending` | `#5B72B3` | `#4A5AA0` | `#EEF1FA` | `#8A9AD6` | `#1A2238` |
| `status-neutral` | `#64748B` | `#566072` | `#F0F2F5` | `#8593A8` | `#1F2839` |

Dark `-text` values are not specified on the board; the dark card instructs: **"Verify every pair
with tooling in CI."** (In dark, status-progress presumably follows `action-accent`/`accent-tint`;
that is a derivation, not a stated value — flag it in review.)

### 2.6 Severity — a separate axis (F12)

Solid fill, white ≥800-weight text, always paired with a score or word. Never restyled as status,
never reused for workflow status.

| Token | Fill | Label text colour beside chip |
|---|---|---|
| `severity-critical` | `#B42318` | `#B42318` |
| `severity-high` | `#E11D48` | `#E11D48` |
| `severity-medium` | `#D97706` | `#D97706` |
| `severity-low` | `#64748B` | `#566072` |

Chip anatomy: score in Inter 800 11px white, padding 3×7, radius 6. **KEV** badge: Inter 800 9px
white +0.27px tracking on `#B42318`, padding 1×5, radius 4.

### 2.7 Dark mode

Same semantic names, one variable collection. **Interactive direction inverts — hover lightens.**
All specified dark values are in the tables above. Tokens marked "not specified" have no stated
dark value on the board and must be derived at implementation time, then contrast-verified in CI.

---

## 3. Typography

Sora for display, Inter for UI. A closed ramp — one style per purpose. Hierarchy via weight and
color before size.

### 3.1 Families

| Family | Role | Weights |
|---|---|---|
| **Sora** | Display · headings · card titles · numerals · code chips | 600 SemiBold · 700 Bold · 800 ExtraBold |
| **Inter** | All UI text — body, labels, captions, tables | 400 · 500 · 600 · 700 |

### 3.2 The ramp — closed set (F3)

Never introduce a size between steps. Tabular numerals mandatory in tables, KPIs, dates.
15 core styles + 4 specialised (code-chip, numeral-lg/md/sm) = the 19 rows below.

| Style | Size / line-height | Family · weight | Tracking | Usage |
|---|---|---|---|---|
| `display-hero` | 52 / 52 | Sora 800 | −3% (−1.56px) | gauge & hero numerals only |
| `display-xl` | 32 / 38 | Sora 800 | −2.5% (−0.8px) | marketing panels only |
| `heading-xl` | 28 / 34 | Sora 800 | −2.5% (−0.7px) | auth headline |
| `heading-lg` | 24 / 30 | Sora 800 | −2% (−0.48px) | page title, one per page |
| `heading-md` | 20 / 26 | Sora 800 | −2% (−0.4px) | drawer & modal titles |
| `heading-sm` | 18 / 24 | Sora 700 | −1% (−0.18px) | large section titles |
| `title-md` | 14 / 20 | Sora 700 | 0 | card titles |
| `title-sm` | 13 / 18 | Sora 700 | 0 | sub-card titles |
| `body-lg` | 14 / 22 | Inter 400 | 0 | prose blocks |
| `body-md` | 13 / 20 | Inter 400 | 0 | default UI text, table cells, inputs |
| `body-sm` | 12 / 17 | Inter 400 | 0 | secondary cells, helper text |
| `label-md` | 13 / 16 | Inter 600 | 0 | button & tab labels |
| `label-sm` | 12 / 15 | Inter 600 | 0 | form labels, facets |
| `caption` | 11 / 15 | Inter 400–600 | 0 | timestamps, meta, badges |
| `overline` | 10 / 14 | Inter 700 | +5% caps (+0.5px) | eyebrows and section labels |
| `code-chip` | 12 / 16 | Sora 700 | 0 | entity codes, accent colored |
| `numeral-lg` | 28 / 32 | Sora 800 | −2% (−0.56px) | KPI values |
| `numeral-md` | 24 / 28 | Sora 800 | −2% (−0.48px) | stat cards |
| `numeral-sm` | 20 / 24 | Sora 800 | −1% (−0.2px) | inline stats |

### 3.3 Numerals

`font-variant-numeric: tabular-nums` in all tables, KPIs, counts and dates. Unit suffixes: 50%
size, Inter 600, text-faint.

### 3.4 Rules

- One `heading-lg` per page — the page title.
- Hierarchy inside a component: weight and color first, size second.
- Links inherit their context size; `text-link` color + 600.
- Mockup half-sizes (12.5, 11.5…) round to this ramp (F3). Deltas ≤ 0.5px.

---

## 4. Space, radius & elevation

4px grid, closed radius scale, borders-first elevation. Shadows mean "floating" — static cards are
border-only.

### 4.1 Spacing scale

2 and 6 exist only inside components (icon–label gaps, pill padding) — F5.

| Token | px |
|---|---|
| `space-05` | 2 |
| `space-1` | 4 |
| `space-15` | 6 |
| `space-2` | 8 |
| `space-3` | 12 |
| `space-4` | 16 |
| `space-5` | 20 |
| `space-6` | 24 |
| `space-8` | 32 |
| `space-10` | 40 |
| `space-12` | 48 |
| `space-16` | 64 |

Aliases: gap-inline 6–8 · gap-related 8 · gap-group 12 · gap-section 16 · gap-region 24 ·
page 24 / 24 / 32 (top / sides / bottom).

### 4.2 Radius — closed scale (F4)

| Token | px | Use |
|---|---|---|
| `2xs` | 4 | checkboxes, KEV badge |
| `xs` | 6 | code chips, small tiles |
| `sm` | 8 | **buttons & inputs** |
| `md` | 10 | inner panels, icon tiles |
| `lg` | 12 | **cards & tables** |
| `xl` | 16 | **modals** |
| `full` | 999 | **pills** |

Child radius never exceeds parent − inset.

### 4.3 Borders

| Width | Style | Use |
|---|---|---|
| 1px | `border-default` solid | all structural borders |
| 1.5px | `border-strong` dashed | add-affordances only |
| 2px | `action-accent` solid | active tab underline, focus outline |
| 3px | status edge-strip | stat & finding cards |

### 4.4 Elevation

Default is 0 — structure comes from borders. Shadow = the element floats.

| Token | CSS | Use |
|---|---|---|
| `shadow-1` | `0 1px 2px 0 rgba(16,24,40,0.05)` | kanban cards, segmented thumb |
| `shadow-2` | `0 6px 16px -8px rgba(16,24,40,0.18)` | hover lift, dropdown menus |
| `shadow-3` | `0 30px 60px -20px rgba(16,24,40,0.4)` | popovers, bulk bar |
| `shadow-4` | `0 40px 80px -24px rgba(16,24,40,0.5)` | modals, command palette |

### 4.5 Icon sizes

12 · 14 · 16 · 20 · 24. Solid icons from Phosphor, mapped once in `components/ui/icon.tsx`:
shapes use the `fill` weight, bare glyphs (check, close, plus, text-format marks) use `bold`,
because their fill variant is the glyph knocked out of a square. 16 default inline · 12 in pills ·
20 in top-bar buttons and feature tiles · brand logos 40 to 48. Changed from 1.8px outline icons on
2026-09-13 at the product owner's request.

### 4.6 Control heights

Button sm 28 · md 36 · lg 44. Inputs 36 (44 auth) · topbar 56 · sidebar item 32 · table header 40 ·
rows 56 / 48 / 40 · pills 20–22 · toggle 38×22.

### 4.7 Z-index

| z | Layer |
|---|---|
| 0 | content |
| 100 | sticky table header |
| 200 | sticky page header |
| 1000 | dropdown / popover |
| 1100 | bulk bar |
| 1200 | drawer |
| 1300 | modal |
| 1350 | command palette |
| 1400 | toasts |
| 1500 | tooltips |

---

## 5. Buttons & forms

One primary per region. Labels are verb + object, sentence case. Fields are required by default —
mark exceptions "(optional)".

### 5.1 Button hierarchy

Primary advances the core workflow · secondary = parallel actions · ghost = dismissive/repeated ·
destructive when destruction is the purpose.

| Variant | Anatomy (light) | Use |
|---|---|---|
| `primary` | fill `action-primary #0369A1`, text white Inter 700 13 | the single main action per region |
| `secondary` | fill white, border 1px `border-default`, text `text-primary` Inter 600 13 | toolbar actions, alternatives |
| `ghost` | no fill/border, text `text-secondary #475467` Inter 600 13 | dismissive, low-emphasis, repeated in rows |
| `destructive` | fill `action-danger #C01741`, text white Inter 700 13 | irreversible primary actions |
| `destructive-2` | fill white, border 1px `#F6CFD8` (rose-200), text `#C01741` Inter 700 13 | reject / revoke inside table rows |
| `success-2` | fill `#E7F5EF` (status-success-bg), text `#08794F` Inter 700 13 | approve / retain inside table rows |
| `link` | text `#0369A1` Inter 600 13, no box | inline navigation ("View all →") |

All buttons: radius `sm` (8), icon–label gap 6.

### 5.2 States

- **default** → **hover** darkens fill (primary `#0369A1` → `#075985`; danger `#C01741` → `#9B1C34`).
  In dark mode the direction inverts — hover lightens.
- **focus-visible**: 2px `action-accent` outline, 2px offset (F9).
- **disabled**: 45% opacity, no pointer events. Prefer explaining why over silently disabling.
- **loading**: spinner (14) replaces the leading icon, label becomes progressive ("Adding…"),
  **width locked**, `aria-busy` set.

### 5.3 Sizes & icon-only

| Size | Height | Padding-x | Icon | Label |
|---|---|---|---|---|
| sm — in-table | 28 | 12 | 14 | Inter 700 12 |
| md — default | 36 | 16 | 16 | Inter 700 13 |
| lg — auth | 44 | 16 | 16 | Inter 700 13 |

Icon-only: 28 (in rows, radius 7) · 36 (toolbar, bordered, radius 8). Icon-only buttons **must**
carry `aria-label` + a tooltip. Never rely on the glyph alone.

### 5.4 Form control anatomy

Label above (6px) · control · helper 6px below. **Never floating labels; placeholders show example
values, never instructions.**

- Label: Inter 600 12 `text-secondary`. Optional marker: ` (optional)` Inter 400 12 `text-faint`.
- Control: h36 (44 on auth), radius `sm` 8, border 1px `border-default`, padding-x 12, value
  Inter 400 13 `text-primary`, placeholder `text-faint #98A2B3`.
- Helper: Inter 400 12 `text-subtle #667085`.
- Select: chevron 15 right-aligned. Search: leading icon 15, placeholder is an example
  ("Search controls…").
- **Focused**: border `#0284C7` + ring `0 0 0 3px rgba(2,132,199,0.15)`.
- **Error**: border `#E11D48` + ring `0 0 0 3px rgba(225,29,72,0.15)`; message 6px below: alert
  icon 14 + Inter 400 12 `#C01741`.
- **Disabled/read-only**: fill `surface-sunken #FBFCFD`, value `text-faint`.

### 5.5 Selection controls

- Checkbox 16×16, radius 4, resting border 1.5px `border-strong #D0D5DD`; checked fill+border
  `#0284C7` with white check 11; indeterminate: white 8×2 bar.
- Radio 16×16 round; selected: 4.5px `#0284C7` ring; resting 1.5px `border-strong`.
- **Toggles 38×22 — instant effect only** (a toggle is never a deferred form input). Label
  Inter 600 13 + description Inter 400 11 `text-subtle`.
- Scale picker (1–5): radiogroup of 66×36 segments, radius 8; selected fill `#0284C7` white
  Inter 700 13, others white with `border-default` and `text-secondary`.

### 5.6 File upload

Dashed 1.5px `border-strong`, radius 12, centered: icon tile 40 (`surface-sunken`, radius 10, icon
20) · "Drag evidence here or **browse**" Inter 600 13 · constraints line Inter 400 11 `text-subtle`
("PDF, PNG, CSV · up to 25 MB").

### 5.7 Error message standard (verbatim)

Say what happened and how to fix it. Validate on blur; re-validate on change once dirty.

**Never**
- "Invalid input"
- "This field is required"
- "Error occurred"
- "Something went wrong"

**Always**
- "Next review must be after Jun 14, 2026."
- "Enter a work email — personal domains aren't allowed."
- "Datadog sync failed — the API key expired Jul 22. Reconnect to resume."
- "File is 32 MB — the limit is 25 MB."

---

## 6. Status & data display

Status is a language: the same word renders the same way everywhere (F7). Color never carries
meaning alone.

### 6.1 Canonical lifecycle map (F7)

The single source of truth. "In progress" was amber on TPRM and blue on the dashboard — it is now
always `status-progress`.

| Family | Status words |
|---|---|
| `status-success` | Passing · Complete · Healthy · Published · Active · Granted · Fixed · Retained · On track · Compliant |
| `status-danger` | Failing · Overdue · Expired · Revoked · Behind · Breached |
| `status-warning` | Needs review · Aging · Due soon · At risk · Degraded · Sync error |
| `status-progress` | In progress · Monitoring · Mitigating · Syncing · Running |
| `status-pending` | Pending · In review · Queued · Awaiting approval · Not started |
| `status-neutral` | Draft · Inactive · Archived · Not applicable · Not configured |

### 6.2 StatusPill anatomy

- **Pill — default.** radius-full · padding 3×9 · dot 6 (`-base`) + caption 11 Inter 700 (`-text`)
  on `-bg`.
- **Inline** — dot 6 + Inter 600 11 `-text`, no background; for dense cells where pills would tile
  noisily.
- **Circles** — 22×22 solid `-base` circle with white icon 13 (check / x); pass/fail test lists,
  decisions.
- **Unknown** — always icon + word (help icon 13 + Inter 600 11 `status-neutral-text`), never a
  bare dot.

**Never**
- A colored dot with no label — fails color-independence (F10).
- Red date text as the only overdue signal — pair with icon or word.
- Green styling for a neutral fact ("12 assets") — success means success.
- A new color for a status that already exists in the map.
- Severity colors reused as workflow status (F12).

### 6.3 Table anatomy

One system, three densities. Header 40 (36 compact). Sortable numerics right-align with
tabular-nums (F11).

| Density | Row height | Use |
|---|---|---|
| comfortable | 56 | entity tables (two-line primary cell: code chip + description) |
| standard | 48 | logs & simple lists (single-line cell) |
| compact | 40 | audit trails, drawers (header drops to 36) |

- Header: `surface-sunken` fill, bottom border `border-default`, labels overline (Inter 700 10,
  +0.5px tracking, uppercase) in **`text-secondary`**, sort icon 13, height 40 (36 compact).
  The colour is load-bearing: the old `text-faint` measured 2.51:1 light and 3.49:1 dark on
  `surface-sunken`, failing AA and the 3:1 non-text floor. `text-secondary` is 7.48:1 / 6.42:1.
  Uppercase is fine; faint was the defect.
- Rows: `surface-primary`, 1px `border-default` between, padding-x 16.
- Alignment: text left; sortable numeric columns right + `tabular-nums`; dates right,
  `text-subtle`.
- Right-alignment uses the TH `numeric` prop, never a `text-right` className.
- Table-owned controls (Columns, Export) render in the `Table` `actions` slot: a right-aligned
  bar inside the table card, above and outside the horizontal scroll area. Page-level actions
  (the primary button, Import, result counts) stay in the `Toolbar`.
- Row hover `surface-hover`; selected row `action-accent-tint`.

### 6.4 Canonical cell patterns

An entity renders identically on every screen it appears.

| Pattern | Spec |
|---|---|
| Code chip | Sora 700 12 `text-link #0369A1` on `action-accent-tint #EAF4FB`, radius 6, padding 2×6 |
| Owner | avatar 24 (initials Inter 700 9.5 white on identity colour, e.g. `#7C3AED`) + name Inter 400 12 `text-secondary` |
| Framework chips | Inter 700 10 on tint, radius 5, padding 2×6 — SOC 2 `#0369A1`/`#EAF4FB`, ISO 27001 `#4A5AA0`/`#EEF1FA` |
| Freshness | StatusPill (e.g. Aging = `status-warning`) |
| Due / SLA — icon + word (F10) | clock icon 11 + Inter 600 11 `status-danger-text` on `status-danger-bg`, radius 6, padding 2×7 ("Overdue 3d") |
| Progress | track 150×7 radius-full `surface-sunken` + 1px `border-default`, fill `status-success-base #059669`, value Inter 700 11.5 `text-secondary` |
| Severity + identifier | severity chip (§2.6) + Sora 700 12 `text-link` code + optional KEV badge |
| Source / vendor | 22×22 brand tile (radius 6) + name Inter 400 12 `text-secondary` |
| Count with icon | doc icon 14 `text-subtle` + Inter 400 12.5 `text-secondary` |

Avatars use the neutral identity ramp — a person is not a status (identity colours are per-user
hashes, not semantic tokens).

---

## 7. Overlays & feedback

Peek → drawer · commit → modal · act-in-place → popover · navigate → page. Avoid unnecessary
modals.

### 7.1 Overlay decision matrix

Sizes are fixed — no arbitrary widths. All trap focus, restore it on close, and close on Esc.

| Surface | Width | Use | Behaviour |
|---|---|---|---|
| Tooltip | max 280 | icon-only buttons, truncated text, definitions | 300ms delay · no actions inside · shows on keyboard focus |
| Popover | 320–400 | notifications, column pickers, help | anchored + 8px offset · caret · outside-click closes |
| Dropdown menu | min 180 | row ⋯, facet menus, user menu | items h32 · arrow-key roving · destructive items last |
| Drawer (right) | 480 / 560 | quick-look a row without losing list context | scrim .45 + blur · deep-linkable `?panel=` · pinned footer |
| Modal | 480 / 600 / 720 max | focused create & edit, confirmations | scrim .50 + blur · beyond 720 or 70vh → use a page |
| Command palette | 640 × 540 | global nav, search, actions | ⌘K · grouped results · kbd legend footer |
| Confirm dialog | 480 | destructive or audit-relevant irreversibles | initial focus = Cancel · type-to-confirm for bulk deletes |

### 7.2 Feedback — which channel when

Never toast a validation error. Never banner a transient success.

| Situation | Channel |
|---|---|
| Field problem | inline under the field |
| Form rejected | alert block + focus moved to it |
| Ongoing condition | page banner |
| Long-running job | inline progress + toast on completion |
| New events | bell badge + notifications popover |

- **Toast** — user-triggered result · 5s. `surface-inverse #101828`, radius 10, padding 12×14,
  icon 16 (status-base colour) + Inter 600 12.5 white; shadow `0 8px 24px -8px rgba(16,24,40,0.4)`.
  z-1400.
- **Inline alert (ErrorBanner)** — form-level problem. `status-danger-bg #FDEEF1`, border 1px
  `#F6CFD8`, radius 10, padding 12×14; alert icon 16; title Inter 700 12.5 `#9B1C34`; body
  Inter 400 11.5 `#C01741`.
- **Banner** — ongoing condition, **one action**. `status-warning-bg #FBF1E4`, border `#F0D9B4`,
  radius 10; icon tile 26 `status-warning-base #D97706` (white icon 15); title Inter 700 12.5
  `#8A4B08`; action button fill `#D97706` white Inter 700 11.5, radius 8.
- **BulkActionBar** — `surface-inverse`, floats with `shadow-3`, z-1100. Bulk destructive shows an
  exact count.

### 7.3 Destructive confirm pattern

Names object + consequence. Card: radius 14, shadow `0 20px 40px -12px rgba(16,24,40,0.28)`; icon
tile 36 `action-danger-tint` (trash 18 danger); title Sora 800 15/20 −0.15px ("Delete this evidence
item?"); body Inter 400 12 `text-subtle` naming the object and consequence ("'Q2 privileged access
review' is linked to CC6.1 and CC6.3. Those controls will lose this evidence."); footer right:
Cancel (secondary, **initial focus**) + destructive fill `#C01741` labelled verb + object ("Delete
evidence"). Type-to-confirm for bulk deletes.

### 7.4 Loading / skeletons

Skeletons mirror the real layout — reserve exact heights, never blank a populated table.

- Bones: header bars `#E4E7EC` h8 radius 4; row blocks `#F2F4F7` (secondary line `#F4F5F7`);
  avatar block 32 radius 8; pill bone 84×20 radius-full. Row heights match the real density.
- Show nothing under 400ms · once shown, hold 300ms minimum.
- Button loading: spinner replaces the leading icon, width locked.
- Background refresh: keep stale data + 2px accent bar under the toolbar.
- Shimmer 1.4s linear.

### 7.5 Empty states

Say what happened and what to do next. Keep the toolbar visible on filtered-empty.

Anatomy: `surface-sunken` panel radius 10 · icon tile 40 `surface-hover` radius 10 (icon 20) ·
title Sora 700 14 · body Inter 400 12 `text-subtle` (name the active filters) · one action.

| Variant | Action |
|---|---|
| First use (no data) | primary action |
| No results (filtered-empty) | **Clear filters** (secondary) — e.g. "No controls match your filters / Try removing 'Status: Failing' or widening the framework filter." |
| No permission | name the person who can grant it |
| Failed | Retry + a reference id |
| Zero-is-good | success check, no action |

### 7.6 Motion

Communicates state change and hierarchy — never decoration. Nothing over 300ms.
`prefers-reduced-motion` → fades ≤50ms only.

| Duration | Use |
|---|---|
| 80ms | hover colour |
| 150ms | control state, tab underline |
| 200ms | dropdown, popover, toast in |
| 250ms | modal & drawer in |
| 200ms | modal & drawer out |
| 1.4s | skeleton shimmer |
| none | chart draw-in |

Easing: `cubic-bezier(0.2, 0, 0, 1)` for state · `cubic-bezier(0, 0, 0, 1)` for entering surfaces ·
linear for shimmer. One property family per transition — no bounce, no parallax.

---

## 8. The 12 flagged changes (F1–F12)

Where the mockups were inconsistent or failed accessibility, the system picks one standard. Each is
referenced in place on the detail pages.

| # | WAS | NOW | WHY |
|---|---|---|---|
| F1 | Filled buttons and links use #0284C7 — white text ≈4.0:1 | Interactive fills and text links use #0369A1; #0284C7 stays the accent | WCAG 4.5:1 for text under 18px |
| F2 | #98A2B3 carries meaningful metadata at ≈2.8:1 | New text-subtle #667085 (≈4.8:1); #98A2B3 becomes decorative-only | AA contrast for readable text |
| F3 | Nine font sizes including half-pixels (9.5–13.5) | Closed integer ramp: 10 / 11 / 12 / 13 / 14 / 16 / 18 / 20 / 24 / 28 | One style per purpose |
| F4 | Ten radii in use: 4, 5, 6, 7, 8, 9, 11, 12, 13, 15 | Closed scale: 4 / 6 / 8 / 10 / 12 / 16 / full | Deltas ≤1px are invisible — they only cost consistency |
| F5 | Off-grid spacing: 9, 11, 13, 22, 26 | 4px grid, with 2 and 6 inside components only | Predictable rhythm |
| F6 | Table headers at 38 and 40; rows at 48 / 52 / 54 / 56 | Header 40 (36 compact); rows 56 / 48 / 40 | One density system |
| F7 | "In progress" is amber on TPRM, blue on dashboard, indigo on risk | Canonical lifecycle → colour map | The same word must mean the same thing |
| F8 | Tint text colours hardcoded per instance | Promoted to status-*-text tokens | Themeable and consistent |
| F9 | Focus is a soft 3px ring only | focus-visible: 2px solid outline + 2px offset | WCAG 2.4.7 / 2.4.13 |
| F10 | Red date text is the only overdue signal in some tables | Colour always pairs with an icon, word or tooltip | Colour-independence |
| F11 | Numeric columns left-aligned | Sortable numerics right-align with tabular-nums | Scanability down a column |
| F12 | Severity and status share reds and ambers ad hoc | Severity is a separate token axis | They answer two different questions |

---

## 9. Review checklist

Run before any design or PR review.

**TOKENS & VISUALS**
- [ ] No raw hex, off-ramp size, off-grid space or off-scale radius
- [ ] Shadows only on floating elements
- [ ] One heading-lg per page
- [ ] Numerals tabular in tables and stats

**SEMANTICS**
- [ ] Status words follow the canonical map
- [ ] No colour-only meaning
- [ ] Text under 18px on tint uses -text tokens
- [ ] text-faint carries no information

**COMPONENTS**
- [ ] One primary button per region; labels are verb + object
- [ ] Tables: correct density, sticky header, right-aligned numerics
- [ ] Detail pages use DetailHeader (with a record icon); module roots use PageHeader + TabStrip
- [ ] Tabs use the TabStrip `bar` style (the default); `compact` only inside narrow embedded panes
- [ ] Dashboards and overviews: headline numbers are StatTile, every chart sits in a ChartCard
      (centred title), legends sit above the chart as solid swatches with counts, rings show the
      total in the centre, and "needs attention" lists use StatRow
- [ ] Registers use one Toolbar
- [ ] Overlay follows peek / commit / act / navigate
- [ ] Forms: labels above, actionable errors, validate on blur

**ACCESSIBILITY**
- [ ] Keyboard path walked; focus visible; Esc retreats
- [ ] Icon-only controls have aria-label + tooltip
- [ ] Contrast verified in light and dark
- [ ] Reduced-motion behaviour defined

**STATES**
- [ ] Loading, empty, filtered-empty and error all designed
- [ ] No layout shift when loading resolves
- [ ] Destructive paths name their consequence
- [ ] Bulk destructive shows an exact count

**CONSISTENCY TRAPS**
- [ ] No new row heights or pill anatomies
- [ ] Same entity renders identically everywhere
- [ ] No modal that should be a drawer or page
- [ ] No toast that should be a banner

---

Machine-readable tokens: [`frontend/src/styles/ds-tokens.json`](../frontend/src/styles/ds-tokens.json).
