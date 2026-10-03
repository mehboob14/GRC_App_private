# Design: public website and documentation revamp

## 1. Reference mapping

The site follows [Harness](https://www.harness.io/) element by element where that serves a GRC buyer.
Where it does not, the substitution is named.

| Harness | Verity |
|---|---|
| White sticky header: logo, Platform ▾, Why Harness, Pricing, Customers, Resources ▾, Company ▾; *See a Demo* (outline) and *Start for Free* (black) | White sticky header: wordmark, Platform ▾, Solutions ▾, Why Verity, Pricing, Resources ▾; *Sign in*, *See a demo* (outline), *Start trial* (black). There is no Customers or Company menu because there is nothing true to put in them yet. |
| Platform mega menu: grouped products with icons and one-line descriptions | Platform mega menu in four groups (Compliance, Risk, Security, Platform). Every item has an icon, a line of description and a Coming soon badge where one applies. A featured card links to the platform overview. |
| Light cool-grey hero; mono eyebrow; two-line serif headline; lead; button pair; animated isometric cubes | The same composition. The isometric art is Verity's own: framework layers, dotted control cubes and evidence cubes that fill in sequence, so the illustration shows "proof assembling". |
| "Built for enterprise scale" strip with mono labels and highlighted numbers | "Ready on day one" strip with numbers from the shipped content library (61 SOC 2 criteria, 114 control templates, 15 policy templates, 60 library risks). No usage metrics are invented. |
| Agent sections (Software Delivery, Security Testing, Runtime Protection, Cost Management): eyebrow, serif H2, lead, *Learn more →*, three icon rows separated by rules, product chips, product-UI composition | Four pillar sections (Prove compliance, Manage risk, Secure the estate, Govern with confidence) in the same anatomy. Chips name sub-capabilities and carry Coming soon badges. The compositions are code-native recreations of Verity screens: a requirement-to-evidence flow with success pills, a risk heat map with an assistant prompt, an asset donut and severity bar, an acknowledgement chart. |
| Chat prompt and "Thought for 6 seconds" agent response | Used only for the AI assistant (Coming soon), labelled as an AI draft that a person must approve. The rule that AI drafts and humans decide is stated next to it. |
| Footer columns and legal row | Footer columns: Platform, Solutions, Frameworks, Resources, Get started. Legal links appear only once real policy URLs are configured. |
| Developer Hub: top bar, product sidebar, breadcrumbs, article, "On this page", feedback, previous/next, search modal, theme toggle | Docs portal with the same anatomy (section 9). |

## 2. Visual system

**Typography.** Display headings use Source Serif 4 (variable, regular to semibold, tight tracking),
matching the reference's editorial serif. Body and UI text use Inter. Eyebrows, labels, figures and
code use JetBrains Mono, upper case with wide tracking for eyebrows. All three are self-hosted
through Fontsource: no third-party font request, so the CSP is unaffected. Scale: hero 56–76px,
section titles 40–52px, card titles 17–20px, body 16–18px, small text 13–14px, never below 12px.

**Colour.** White surfaces; hero gradient from cool grey `#E8EDF2` to white; ink `#0B0F17`; body
`#363F4E`; muted `#5D6878`; hairlines `#E3E7EC`. Primary action is near-black, secondary is white
with a hairline border, and links are accent blue `#0A6CCB`. The illustration palette is Verity's sky
ramp (`#E0F2FE` → `#0369A1`), which matches the reference's light-blue cubes. Status colours are
the product's own, so recreated screens look like Verity: pass/success green, warning amber,
fail/critical red, high orange, info blue, neutral grey. Coming soon badges are soft indigo
(`#EEF2FF` on `#4338CA`), a colour status never uses, so a badge cannot be confused with a state. All
text meets WCAG AA.

**Layout.** 1280px content frame with faint vertical rules at its edges, as in the reference.
Sections separated by hairlines; 96–128px vertical rhythm on desktop, 64–80px on mobile; 16px side
gutter at phone width; no horizontal scroll at 360px.

**Components.** Buttons (dark, outline, text-with-arrow); eyebrow; section header; feature row
(icon, title, line, separated by rules); chip; status badge (Live, Preview, Coming soon); product card
(white, 1px border, soft neutral shadow, 12px radius); status pill; severity pill; data table;
donut, bar, stacked bar, gauge and heat-map charts drawn as inline SVG; chat bubble and assistant
response; flow step; KPI tile; avatar initials; control-code chip; mega menu; mobile drawer; modal
dialog; drawer; accordion; tabs; tooltip.

**Motion.** Elements reveal on entering the viewport: opacity plus 12–16px translate, 450–600ms,
with a stagger. Charts animate from zero, flow steps light up in order, the isometric hero cycles
gently, and counters count. Menus and dialogs use 150–200ms fades and scales. With
`prefers-reduced-motion: reduce`, nothing moves and every element renders in its final state.
Animation never carries information that the static state lacks. Motion uses CSS and an
IntersectionObserver hook, with no animation library.

**Accessibility.** Semantic landmarks and headings; skip link; visible focus rings. Menus are
disclosure buttons with `aria-expanded`, closed by Escape and by clicking outside, and open on hover
only for fine pointers. Dialogs trap focus and return it on close. Charts carry text equivalents.
Badges are text, not colour alone. Every interactive element can be reached by keyboard.

## 3. Status model and the single source of truth

`website/content/catalog.ts` lists every module, capability, integration and framework with a
`status` of `live`, `preview` or `soon`. Navigation, pages, chips, the pricing table, the framework
library and the docs sidebar all read it. One status value changes every place that shows it.

- **live**: generally available in the product today (as the user guide describes).
- **preview**: visible in the product but showing illustrative data (the executive Dashboard).
- **soon**: planned or under consideration. Rendered with a Coming soon badge, and on its own page
  with a banner. Copy for these items uses "will" and states no dates.

What is live today: frameworks and controls (SOC 2 library), evidence, policies and documents with
acknowledgements, tasks with SLAs and approvals, risk register (scoring, treatment, acceptance,
library), third-party risk (the twelve-stage lifecycle), assets, vulnerabilities, the GitHub
connector with seven automated checks, people, roles, groups, two-factor policy, time-boxed auditor
access windows, custom fields, and the append-only audit log.

What is shown as Coming soon: additional framework libraries (ISO 27001, PCI DSS, HIPAA, GDPR, NIST,
regional banking and government frameworks, SOC 1 and SOC 3), more connectors (AWS, Okta, Microsoft
365, Google Workspace and the rest of the catalogue), continuous monitoring with findings and
alerts, configurable approval workflows, Jira and Slack, enterprise risk (RCSA, KRIs, incidents,
risk appetite), business continuity, CIS benchmarks, single sign-on, full access reviews, Trust
Center, questionnaire automation, security awareness training, device monitoring, and the AI
assistant and AI drafting.

## 4. Information architecture

```
/                               Home
/platform/                      Platform overview (every module, by group, with status)
/platform/<module>/             18 module pages (8 live, 10 coming soon)
/solutions/<industry>/          banking-financial-services, fintech-payments, healthcare,
                                saas-technology, government-public-sector
/frameworks/                    Framework library (filter by region, category, status; details popup)
/why-verity/                    Why Verity
/pricing/                       Plan tiers, comparison table, Talk to sales
/security/                      Security at Verity
/demo/                          Demo request (also a popup everywhere)
/docs/                          Documentation home
/docs/<section>/<page>/         Documentation pages
```

Modules: compliance-automation, evidence-management, policy-management, trust-center*,
questionnaire-automation*, risk-management, third-party-risk, enterprise-risk-management*,
business-continuity*, asset-inventory, vulnerability-management, continuous-monitoring*,
device-monitoring*, access-reviews*, security-awareness-training*, integrations,
workflows-and-approvals, ai-assistant* (`*` = coming soon).

## 5. Homepage narrative and why each section is there

The order follows **AIDA** (attention, interest, desire, action) at page level. The problem
section uses **PAS** (problem, agitate, solve). The plan and closing sections use the **StoryBrand**
pattern (the buyer is the hero, Verity is the guide, a short plan, a clear call to action). Each
section answers the question a buyer has at that moment of the scroll.

| # | Section | Buyer's question | Why it is built this way |
|---|---|---|---|
| 1 | Header with mega menus | "What is here, and how do I act?" | Shows the platform's breadth in one glance. Both conversion paths stay visible: a demo for considered, committee-led buyers (banks) and a trial for self-serve evaluators. |
| 2 | Hero: eyebrow *Compliance as a service, end to end*; H1 *Your source of truth for compliance and security*; lead; See a demo / Start trial; isometric proof-assembling art | "What is this, and is it for me?" | Passes the five-second test: category, outcome and audience in one screen. The name Verity means truth, and the headline earns that. The art shows the mechanism (requirements → controls → evidence) instead of decorating. |
| 3 | Ready on day one: library numbers | "Is it real?" | Concrete, checkable numbers build credibility early without fabricated logos or usage metrics. |
| 4 | Problem: compliance work is scattered | "Do they understand my situation?" | PAS. Buyers recognise their own pain (spreadsheets, duplicate effort per framework, stale evidence, invisible vendors, audit-week scramble) before they will evaluate a fix. Kept short so it does not read as fear selling. |
| 5–8 | Four pillar sections | "Can it do my job?" | Each is written for one buyer's job (compliance lead, risk officer, security lead, policy owner). The headline states an outcome, three rows give the proof points, chips show breadth and honest status, and a product composition shows the workflow. Detail continues on the module pages. |
| 9 | AI that drafts, people who decide (Coming soon) | "Where is the AI?" | Meets the market's expectation and states the governance rule that regulated buyers need to hear: AI never approves, publishes or changes a record. |
| 10 | How it works: four steps | "How hard is it to start?" | StoryBrand's plan. Four steps (choose frameworks, assign owners, collect and connect, monitor and prove) reduce perceived switching risk. |
| 11 | One record, every relationship | "Why Verity rather than another tool?" | Shows the product's unique mechanism (a vulnerability traced to its asset, risk, control, policy and evidence) and "map once, satisfy many". It is shown, not claimed. |
| 12 | Frameworks you answer to | "Does it cover my regulator?" | Regulated buyers search by regulation name. Coverage grouped by region (Global, United States, Pakistan, UAE, Australia, EU), each item with an honest status, linking to the library. |
| 13 | Built for your industry | "Is it built for organisations like mine?" | Self-segmentation into tailored pages, which also serve industry search queries. |
| 14 | Integrations | "Will it fit our stack?" | Answers the integration objection with the real catalogue: GitHub live, the rest badged. |
| 15 | Security at Verity | "Can we trust the vendor itself?" | Usually a bank's first procurement question, answered with verifiable architecture facts from the platform. |
| 16 | Documentation | "Can my team use it?" | Public, task-based documentation signals maturity and lets end users try before they buy. |
| 17 | FAQ | "What about…?" | Handles the remaining objections: frameworks, certification, data handling, AI, pricing, getting started. |
| 18 | Final call to action | "What do I do now?" | Restates the outcome with the same two actions, plus small proof text. |
| 19 | Footer | "Where is…?" | Navigation safety net and crawlable site map. |

## 6. Module page template

Hero (breadcrumb, eyebrow naming the group, serif H1 stating the job, lead, actions, status badge,
product composition) → at-a-glance facts → three or four alternating feature rows, each with its own
composition → capability grid → "Works with" (connected modules, showing linkage) → documentation
links → FAQ → closing call to action.

*Reasoning:* the hero answers "what job does this do"; the feature rows show proof; the grid lets a
skimming reader check the full scope; the connected modules show that the value compounds across the
platform; docs links let an end user verify the detail.

The **coming-soon variant** opens with a banner that says the module is planned and names what is
available today instead. It then covers what it will do, how it will connect to the live modules,
and a "Tell us what you need" action that opens the demo form with the module preselected. It never
shows numbers or claims usage.

## 7. Industry page template

Hero in the industry's own language → the obligations buyers in that industry face (from verified
regulation names in the target markets) → how Verity helps, mapped to modules → the frameworks they
answer to, by region and with status → an example workflow (animated stepper) → FAQ → call to
action.

*Reasoning:* relevance beats breadth. Naming the buyer's actual regulator and obligations earns
attention that generic copy cannot.

## 8. Framework library, pricing, why, security

- **Framework library:** a hero explaining "map once, satisfy many" with an animated mapping of one
  control to several frameworks, then filters (region, category, status, text search) over cards.
  Each card opens a details popup: issuer, version, what it covers, who it is for, status. A note
  says that certification or attestation comes from an auditor or certification body; Verity
  prepares the work.
- **Pricing:** four tiers named by organisational need (Essentials, Growth, Enterprise, Regulated),
  with no prices. Each tier has a Talk to sales action that opens the demo popup with the tier
  preselected. A comparison table marks every row Included, Coming soon or —. A FAQ explains what
  pricing depends on. Tier contents live in `content/pricing.ts`; they are a packaging proposal for
  the product owner to confirm.
- **Why Verity:** the differentiators as demonstrations (connected records, map once, error is not
  fail, humans approve AI, isolation and audit trail), plus a comparison of spreadsheets, point
  tools and Verity by capability, naming no competitors.
- **Security:** only verifiable facts. Database-enforced workspace isolation with automated
  isolation tests; roles, groups and granular permissions; a two-factor requirement for administrators; a
  12-character password policy; time-boxed auditor access windows; an append-only audit log enforced by the
  database; secrets encrypted at the application layer; evidence files in object storage;
  read-only, least-privilege connector tokens; AI governance. Single sign-on is Coming soon. No
  certification is claimed.

## 9. Documentation portal

**Content.** `website/content/docs/<section>/<page>.mdx` with YAML front matter (`title`,
`description`, `status`, `updated`). `content/docs/nav.ts` orders the sidebar groups: Get started,
Compliance, Policies, Work management, Risk, Third-party risk, Security operations, Integrations,
Administration, Roadmap (coming-soon features), Reference. The 13 guide chapters become about 45
task-sized pages. Live behaviour is described only as the guide and the code describe it.

**Pipeline.** At build time `lib/docs.ts` reads the files, parses front matter with `yaml`, and
compiles MDX with `@mdx-js/mdx` (remark-gfm, rehype-slug, and a plugin that collects h2/h3 for the
contents rail). Pages render as static HTML through `app/docs/[[...slug]]/page.tsx`. The build
fails with the file name and reference on: a broken internal link or fragment, a missing screenshot,
missing alt text, invalid front matter, an unknown component, or a page that is missing from or
duplicated in the nav.

**Components available in MDX** (no imports): `Callout` (note, tip, warning, soon), `Steps`/`Step`,
`Tabs`/`Tab`, `Screenshot` (frame, caption, click to zoom), `Walkthrough` (numbered hotspots from
screenshot element boxes, stepped with keyboard or buttons), `Lifecycle` (animated stage diagram),
`Cards`/`Card`, `Status`, `Kbd`.

**Shell.** Top bar (docs wordmark, sections, ⌘K search, theme toggle, Start trial), collapsible
sidebar with group icons and Coming soon badges, breadcrumbs, article (max ~760px), "On this page"
rail with scroll-tracked highlight, reading-progress line, copy-link heading anchors, "Was this page
helpful?" (shown only when a feedback endpoint is configured), previous and next cards. On mobile
the sidebar becomes a drawer and the contents become a dropdown. Light and dark themes follow the
system setting, can be toggled, and the choice is remembered on the device.

**Search.** A build-time index of every page's title, headings and section text, served as a static
JSON file. A client-side ranker scores title and heading matches above body matches, supports
prefix matching, and returns section-level results with highlighted excerpts. Opened with ⌘K, Ctrl+K
or `/`. Arrow keys move through results, Enter opens one, Escape closes the search. An empty result
offers the documentation home.

**Screenshots.** Captured from the running application with demonstration data at 1440×900 and 2×
density, with the temporary third-party logo replaced by the Verity mark at capture time. They are
stored as optimised WebP in `public/docs/screens/`, with a manifest of dimensions and element
boxes (the source for walkthrough hotspots). Every screenshot is labelled as demonstration data.

## 10. Demo request popup

Fields: first name, last name, work email, company, job title, country, organisation size, areas of
interest (multiple choice: frameworks and modules), message (optional), and a consent checkbox to be
contacted. A hidden honeypot field and a minimum fill time reject simple bots. The form validates in
the browser, then POSTs JSON to `NEXT_PUBLIC_DEMO_ENDPOINT` with `credentials: "omit"`. A 2xx response
shows a success state. Anything else shows an error with the option to try again. The endpoint must
be HTTPS, and the build fails on a malformed value. When unset, the submit button is disabled and
the form says that requests are not being sent yet. The same component renders in the popup and on
`/demo/`. A "Talk to sales" or module "Tell us what you need" action preselects its interest. No
personal data is stored in the browser.

## 11. Internationalisation readiness

Marketing copy lives in `website/content/*.ts` modules, and components receive text through props.
Layout uses logical properties (`margin-inline`, `inset-inline-start`, `text-align: start`), and
`<html lang dir>` comes from site config. Adding Arabic or Urdu later means a locale segment, a
translated content module and a right-to-left review. No redesign is needed.

## 12. Dependencies

| Package | Why it is worth it | Replaces |
|---|---|---|
| `@mdx-js/mdx` | Compiles website-owned docs with interactive components at build time. It ships nothing to the browser beyond the rendered components. | `react-markdown`, `remark-parse`, direct `unified` use |
| `yaml` | Parses front matter. No dependencies of its own, widely used. | — |
| `@fontsource-variable/source-serif-4` | Self-hosted display serif for the reference's editorial typography. | `@fontsource/sora` |
| `@fontsource-variable/jetbrains-mono` | Self-hosted monospace for eyebrows, labels and figures. | — |
| `@phosphor-icons/react` | The icon set the product itself uses (`frontend/` depends on it), so the site and the screenshots speak one visual language. Icons are imported individually from its server-safe entry, so only the glyphs used are shipped. | Hand-drawn inline SVG icons |

Removed because nothing uses them: `react-markdown`, `remark-parse`, `unified`,
`mdast-util-to-string`, `@fontsource/sora`. `github-slugger` stays so the contents rail and search
index produce the same anchors as `rehype-slug`. The `postcss` dev dependency moves from 8.5.6 to
8.5.28 to clear published advisories (`npm audit` reports none afterwards).

No animation, chart or search library is added. Those are built in-house with SVG, CSS and small
hooks.

## 13. Security and privacy

Static export only. No cookies, analytics or third-party scripts. The demo and feedback forms are
the only network calls, go only to configured HTTPS endpoints, and send no cookies. The CSP stays
restrictive, and `connect-src` gains the endpoint origin only when one is configured. The
`nginx.conf` example and README document this. Theme preference is the only thing stored on the
device. Screenshots contain demonstration data only.

## 14. Verification

Typecheck, lint, unit tests (content catalog integrity, docs validation, search ranking, endpoint
configuration), and a production build. Static route smoke tests cover every page. A Playwright
review covers every page at 1440 and 390 widths: no horizontal scroll, menus, popup, drawer,
search, theme toggle, keyboard traversal and reduced motion. Copy review checks every Live claim
against the user guide and code, and checks that every unbuilt item shows its badge.

## 15. Open items for the product owner

Prices (deliberately absent); confirmation of the tier packaging; legal pages (privacy, terms);
company contact details and social links; the demo endpoint; the feedback endpoint; the public
domain (`SITE_URL`). The site hides links to anything not configured. It never shows placeholders.
