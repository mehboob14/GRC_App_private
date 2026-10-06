# Verity public website and documentation

The marketing site and the public documentation for Verity, as one static Next.js export. It is
independent of the authenticated app in `frontend/`: no product API, database, tenant context or
cookies. The change that specifies it is `openspec/changes/revamp-public-website/` (it supersedes
the presentation parts of `add-public-website`).

The structure, layout, motion, menus and documentation experience follow the reference the
product owner chose ([Harness](https://www.harness.io/) and its developer hub). The content,
artwork and brand are Verity's own.

## Versions

| Version | Where | What |
|---|---|---|
| v2 (this) | `codex/public-website` | The full platform story, industry pages, framework library, pricing tiers, MDX docs |
| v1 | git tag `website-v1` (commit `931b924`) | The previous site. Restore with `git checkout website-v1 -- website/` |
| v0 | `../website-v0-source-2026-10-01.zip` | The first design, before the earlier Harness-informed pass |

## Local development

Node 22 or later. From `website/`:

```bash
npm ci
npm run dev          # http://localhost:3001
```

| Command | What it does |
|---|---|
| `npm run typecheck` | TypeScript |
| `npm run lint` | ESLint (Next config) |
| `npm test` | Content honesty checks, docs validation, search ranking, configuration |
| `npm run check:docs [files]` | Fast MDX checks while writing docs |
| `npm run build` | Validates every docs page, then exports static HTML to `out/` |

## Configuration (build time)

| Variable | Required | Purpose |
|---|---|---|
| `SITE_URL` | production | Canonical HTTPS origin of this site |
| `APP_URL` | no | Verity app origin (default `https://runwaydream.com`); Start trial → `/sign-up`, Sign in → `/sign-in` |
| `NEXT_PUBLIC_DEMO_ENDPOINT` | no | HTTPS endpoint that receives demo requests as JSON. Unset: the form says nothing is sent and submit stays disabled |
| `NEXT_PUBLIC_FEEDBACK_ENDPOINT` | no | HTTPS endpoint for "Was this page helpful?" on docs pages. Unset: hidden |
| `PRIVACY_URL`, `TERMS_URL` | no | Approved policy pages. Unset: no legal links are shown |

The build fails on a malformed URL. `.env.example` shows the shape; its example domain must never
ship.

**Demo request payload** (POST, `Content-Type: application/json`, no cookies):
`firstName, lastName, email, company, jobTitle, country, organisationSize, interests[], tier, message, consent, source, page`.
A 2xx response shows the success state; anything else offers a retry. Bots are filtered with a
honeypot field and a minimum fill time before anything is sent.

## Where things live

```
app/(site)/            marketing routes: home, platform, platform/[module], solutions/[industry],
                       frameworks, why-verity, pricing, security, demo
app/docs/              docs layout and [[...slug]] (articles, docs home, redirects from old URLs)
app/search-index.json/ the docs search index, generated at build
components/site/       header, mega menus, mobile drawer, footer, demo popup and form
components/sections/   page sections and templates
components/visuals/    isometric hero art, charts and product-interface compositions
components/docs/       docs shell (sidebar, contents, search, theme) and MDX components
content/               all copy and data (see below)
content/docs/          documentation MDX, nav.ts (sidebar order), screens.json (screenshot manifest)
public/docs/screens/   product screenshots (WebP)
```

### Content and the status rule

`content/catalog.ts` is the single source of truth for what exists and whether it is available:
`live`, `preview` or `soon`. Menus, pages, chips, the pricing table and the docs read it, and every
`soon` item renders a **Coming soon** badge. When something ships, change its status there and on
its docs page's front matter (`npm test` fails if they disagree).

| File | Holds |
|---|---|
| `content/catalog.ts` | modules, groups, integrations, GitHub checks, library facts |
| `content/home.ts` | homepage copy (section order and reasoning: design.md §5) |
| `content/modules.data.ts` | the 18 module pages |
| `content/industries.data.ts` | the 5 industry pages |
| `content/frameworks.data.ts` | the framework library (60 entries, checked against official sources in October 2026) |
| `content/pricing.ts` | plan tiers and the comparison table (a packaging proposal; no prices) |
| `content/navigation.ts` | menus and footer, derived from the catalog |

Copy rules: plain language for the people who use Verity; British spelling, matching the product;
no invented customers, metrics, certifications or prices; anything not generally available says so.
`npm test` checks the library numbers against `backend/src/verity/seed/content/` and the GitHub checks
and integration statuses against the automation content.

Copy lives in these modules, not in components, so a locale can be added later. Layout uses
logical CSS properties, and `<html lang dir>` comes from `lib/site-config.ts`.

## Documentation

Pages are MDX in `content/docs/<section>/<page>.mdx`, ordered by `content/docs/nav.ts`. Front matter:

```yaml
---
title: Controls
description: One or two sentences for search results and link previews.
status: live        # live | preview | soon (soon adds the Coming soon banner and badge)
updated: 2026-10-02
---
```

No level-1 heading (the title is the H1). Internal links are absolute with a trailing slash:
`[Evidence](/docs/compliance/evidence/#keep-evidence-fresh)`. Components, with no imports:

| Component | Use |
|---|---|
| `<Callout type="note\|tip\|warning\|soon" title="…">` | Context, shortcuts, "Before you click" warnings |
| `<Steps>` + `<Step title="…">` | Numbered walkthroughs |
| `<Tabs labels={[…]}>` + `<Tab>` | Alternatives the reader chooses between |
| `<Screenshot name="…" alt="…" caption="…" />` | A framed screenshot that enlarges on click |
| `<Walkthrough name="…" alt="…" steps={[{ target, title, body }]} />` | Numbered hotspots on a screenshot; `target` is an element key from `screens.json` |
| `<Lifecycle title="…" stages={[{ name, note }]} />` | A process with stages |
| `<Cards>` + `<Card title href icon>` | Link grids |
| `<Status value="soon" />`, `<Kbd>` | Inline badge, keyboard key |

Put a blank line after an opening tag and before a closing tag when it contains Markdown. The build
(and `npm run check:docs`) fails on a broken link or fragment, a missing screenshot or alt text, invalid
front matter, an unknown component, or a page missing from `nav.ts`. Old `/docs/NN-chapter/`
addresses redirect to their new pages.

Search: the build writes `/search-index.json` from the MDX source; the ⌘K dialog ranks title and
heading matches first. The docs have light and dark themes (the choice is remembered on the device).

## Screenshots

Product screenshots are captured from the running application with demonstration data at
1440×900 CSS pixels, 2× density, with the Verity mark in place of the app's temporary logo. Convert a
capture run into the WebP files and the manifest:

```bash
npx tsx scripts/sync-screens.ts --from <capture-dir>   # PNGs + manifest.json with element boxes
```

Element boxes in `content/docs/screens.json` drive `<Walkthrough>` hotspots. Without `--from`, the
script converts the older 1× captures in `../docs/user-guide/images/` and paints the Verity mark over
the temporary logo.

## Social image

```bash
npm run dev
npx -y -p playwright@1.56.1 node scripts/generate-og.mjs   # writes public/og.png from the live hero
```

## Hosting

Deploy `out/` to any static host or CDN on its own origin. [nginx.conf](nginx.conf) is an example:
terminate HTTPS and set HSTS at the edge, serve `404.html` for unknown routes, and keep the security
headers. The CSP allows inline script and style because the static export inlines hydration data; it
blocks third-party scripts, frames and network calls. **If you set a demo or feedback endpoint, add its
origin to `connect-src`.** No runtime Node process is needed.

This repository deploys it as a Docker image next to the platform: see
[docs/runbooks/website.md](../docs/runbooks/website.md).

## Motion and accessibility

Animations use CSS and one IntersectionObserver; with reduced motion requested, everything renders
in its final state. Menus, dialogs, tabs, search and walkthroughs are keyboard operable, and dialogs
return focus to whatever opened them. Pages are checked at 1440 and 390 pixels wide with no
horizontal scroll.

## Before going live

- Set `SITE_URL` to the approved public domain and check `APP_URL` still serves `/sign-up` and `/sign-in`.
- Connect a reviewed demo endpoint (privacy notice, abuse controls, delivery test), then add its origin to the CSP.
- Confirm the plan packaging in `content/pricing.ts`; prices are intentionally absent.
- Add approved privacy and terms URLs, company contact details and social links when they exist.
- Review the framework library's regional entries with someone who works with those regulators.
