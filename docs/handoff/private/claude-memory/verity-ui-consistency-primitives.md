---
name: verity-ui-consistency-primitives
description: "Platform-wide UI consistency pass: DetailHeader/PageHeader/TabStrip/Toolbar/SegmentedControl/CodeChip/useTableSort primitives, the type-overline contrast fix, and the tsconfig typecheck gotcha"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f1663f-14a9-4f46-8f2f-956fdfa856a3
  modified: 2026-09-03T17:02:33.260Z
---

**VERITY UI CONSISTENCY PASS (2026-09-02).** In `C:\Development\Verity_GRC_Platform\frontend`.
User asked for four things to be consistent "like Vanta/Drata": (1) one back-nav idiom with a
real arrow, left-aligned above the title, with chips moved BELOW the title; (2) delete the
count/summary subtitle under register titles so tabs move up; (3) search + filters + buttons on
ONE row that stretches instead of scrolling; (4) legible, consistent table column headers.
Approved extras: SegmentedControl + CodeChip, wire column sorting, tasks register to a headed
table. Decision: **drop ALL page subtitles everywhere, no exceptions.** See
[[verity-design-reskin]], [[verity-vulnerabilities-module]].

## The gotcha that matters most

**`npx tsc --noEmit` at the frontend root CHECKS NOTHING.** `tsconfig.json` is a solution file
with `"files": []` and project references. Always use **`npx tsc --noEmit -p tsconfig.app.json`**
(and `-p tsconfig.node.json`). `vite build` does NOT catch type errors either (esbuild strips
types without checking). Running the wrong command hid 3 real pre-existing errors: invalid
`Badge` variants `"success"`/`"danger"`/`"warning"` in assets-import-page and
assets-register-page, which made `variants[variant]` undefined so those badges rendered with no
colour at all. Fixed to statusPass/statusFail/countWarn.

## New shared primitives (src/components/ui/, all exported from the barrel)

- `DetailHeader` - back link (`arrowleft`), h1 `text-heading-lg`, then `chips`, `meta`,
  `actions`. Chips ALWAYS below the title. `backTo` optional (tasks embeds it in a pane).
  Replaced 4 back idioms + 2 breadcrumbs across 11 files. Label is "Back to <sidebar noun>";
  "inventory"/"library"/"register" retired as module-root names.
- `PageHeader` - eyebrow + title + actions, **no description slot and no count slot by
  construction**, so a subtitle cannot drift back in.
- `TabStrip` - the one section strip; link mode (routes) or button mode (`value`+`onSelect`);
  `count` badge per tab is where deleted subtitle numbers go; `aside` slot for a standing figure.
- `Toolbar` - search slot is `min-w-0 max-w-[420px] flex-1 basis-56`, actions `ml-auto shrink-0`,
  `flex-wrap` only as last resort. Every per-page SearchInput width override deleted.
- `SegmentedControl`, `CodeChip` - replaced 4 and 3 hand-rolled copies.
- `useTableSort(initialKey, accessors, initialDir)` - `TH` had shipped
  `sortable/sorted/onSort/aria-sort` since day one with ZERO consumers, so no column header in
  the product was ever clickable. **Pass `null` as initialKey (the default) to preserve server
  order** - all 7 registers do, because server order encodes real ranking (audit newest-first,
  vulns risk-ranked, tasks SLA-ranked). Forcing an initial column silently reverses the audit log.
  Do not call setState updaters with side effects inside (StrictMode double-invokes them).
- Deleted `tabs.tsx` (Radix, vertical, pill-styled, zero consumers).
- `Table` has an **`actions` slot**: a right-aligned bar inside the table card, rendered OUTSIDE
  the inner horizontal-scroll div so it stays put while columns scroll. Columns and Export live
  there (all 10 registers); page-level actions (primary button, Import, "Showing n of m") stay in
  `Toolbar`. Outer div is `overflow-hidden` + inner `overflow-x-auto`; safe because
  DropdownMenuContent is portaled to the document root so menus are never clipped.
  KNOWN divergence from the reference: all 10 registers render `<EmptyState>` as a SIBLING of
  `<Table>`, so on an empty result the header row and the Columns/Export bar disappear. The
  reference keeps them (it renders an empty message inside the table, which is what the unused
  `TableEmpty` primitive does). Left as-is pending a decision.
- `useColumnPrefs(storageKey, columns, defaultHidden)` in `use-column-prefs.ts` + `ColumnPicker`
  in `column-picker.tsx` (SPLIT into two files: a hook and a component in one file trips the
  `react-refresh/only-export-components` lint this repo enforces). Only 2 of 14 tables had a
  column picker and they were byte-identical duplicates; now all **10 module registers** have it
  (assets, audit, controls, documents, evidence, groups, roles, team, tasks, vulnerabilities).
  Rules: identity column and structural columns (selection checkbox, trailing actions) are NEVER
  toggleable; the picker now lives in the **`Table` `actions` slot** (it briefly sat in the
  Toolbar; the user asked for it to be part of the table). Existing storage keys
  `verity.controls.columns` and `verity.documents.columns` were preserved so saved reader
  preferences survived the refactor. Detail-page sub-tables and transient import previews get NO
  picker. Two invariants to re-check after any column edit: **every gated TH needs its matching
  gated TD** (verify by counting `isVisible("key")` occurrences per key, must be even) and any
  spanning row's `colSpan` must be computed, not literal (this codebase has zero colSpan because
  empty/loading states render as siblings of `<Table>`, not rows inside it).

## Shell reconstruction — unified top bar + workspace switcher moved (2026-09-03)

User asked to (1) move the **workspace switcher** from the top bar to the **bottom-left of the sidebar**, opening **upward**; (2) move each module's **heading + tabs into a unified two-row top bar** (row 1 = module title left + help/bells/account right; row 2 = the module tab strip), **drop the eyebrow**, keep the account menu top-right. Confirmed both via AskUserQuestion.

**Key pattern — DON'T rewrite the 15 pages; relocate via a portal context.** `src/components/layout/shell-header.tsx` = `ShellHeaderProvider` (in `app-layout.tsx`, wraps Topbar + main) exposing `{title,setTitle,tabsSlot,setTabsSlot}` + `useShellHeader()` (undefined outside shell). `PageHeader` now `useEffect(setTitle(title))` and renders `null` in-shell (eyebrow dropped; inline fallback kept for outside-shell). `TabStrip` `createPortal`s its tabs into `tabsSlot` (a `<div ref={setTabsSlot} className="px-5 empty:hidden">` on the Topbar's row 2 — `empty:hidden` collapses the row on tab-less pages); falls back to inline when no shell. Gotchas: depend on the **stable `setTitle`** (destructured), NOT the context object (new identity each provider render → loop); `if (shell) return null` for one frame before the ref-callback sets the slot avoids a flash of misplaced tabs. **Detail pages** (document-detail, task-detail) pass the new **`inline` prop** to TabStrip so their **record-level** tabs stay in content beside their `DetailHeader` (only module-root tabs hoist to the top bar). Topbar shows a **nav-derived fallback title** (`navTitleForPath` off NAV_SECTIONS/FOOTER_ITEMS) on pages with no `PageHeader` (detail pages). `WorkspaceSwitcher` (new file) owns the switch logic moved out of Topbar; its DropdownMenuContent uses `side="top"`. `SettingsPageHeader` is a DIFFERENT component (own h2) — unaffected. tsc(-p app)/eslint/build clean; verified via static mock only (live login still blocked by the preview-browser session-reset bug).

## The contrast fix (issue 4 was a real a11y defect, not taste)

`.type-overline` was `text-text-faint`, giving table headers **2.51:1 light / 3.49:1 dark** on
`surface-sunken` - failing AA (4.5:1) and even the 3:1 UI floor. Two causes: the design doc
`docs/design-system.md` 6.3 explicitly MANDATED `text-faint`, and the utility is emitted after
Tailwind's colour classes so the ~10 call sites that hand-wrote `text-text-subtle` beside it
**silently lost on source order**. Fixes: `.type-overline` -> `text-text-subtle`; `TH` label span keeps the
uppercase overline but at **`text-text-secondary`**, with the sort hover moved onto a `group` on
the button (it never applied before). Measured live: **7.48:1 light / 6.42:1 dark** for headers,
4.84 / 4.88 for eyebrows.

**IMPORTANT correction (same day):** I first changed headers to sentence case AND fixed the
colour. The user then pointed at a reference screenshot (the GRC-Tenant app) showing UPPERCASE
headers and said to match it. Only the COLOUR was ever the defect, so headers are back to
uppercase overline at text-secondary. Do not "fix" uppercase again. Column labels stay written
sentence case in JSX because the CSS uppercases them. Also updated
`docs/design-system.md` 6.3 AND `src/styles/ds-tokens.json` (overline usage note) so code and
spec stop diverging. Column labels are now written sentence case in JSX ("Trust services").
`arrowl` stays `ChevronLeft` because Pagination depends on it; the new true arrow is `arrowleft`.

## Verifying UI without credentials

The app has MSW mocks: `.env.mock` (`VITE_USE_MOCKS=true`) + launch config `verity-mock` running
`npm run dev --prefix <path> -- --mode mock --port 5174`, so a second dev server runs on 5174
without touching the user's 5173. Dark theme is a **`.dark` class on documentElement** (not
`data-theme`) - set by `src/lib/theme-provider.tsx`. Contrast can be measured with
`javascript_tool` by injecting a probe element and reading `getComputedStyle`. NOTE: `await
requestAnimationFrame` HANGS when the Browser pane is hidden; do not await rAF there. Full
click-through still needs a login and entering credentials is off-limits, so ask the user to
sign in when visual proof of layout is needed.
