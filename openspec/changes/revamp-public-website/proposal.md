# Revamp the public website and documentation: the full platform story, Harness-matched

## Why

The first public site (`add-public-website`, now tagged `website-v1`) explains the shipped SOC 2
workflows carefully, but it describes a SOC 2 tool. The product being built is broader: a
compliance and security platform, delivered as software, that takes any organisation from "we need
to comply" to "we can prove it, continuously", across many frameworks. The first buyers are banks
and regulated organisations in Pakistan (including the State Bank of Pakistan as an organisation),
the United Arab Emirates, Australia and the United States. Buyers like these judge a platform's
whole direction: framework coverage beyond SOC 2, continuous monitoring, vendor and enterprise
risk, and the trust features their own customers ask them for. The site has to show that whole
direction honestly, look and behave like a best-in-class platform site, and give the people who use
Verity documentation that matches the quality of the product.

The product owner named [Harness](https://www.harness.io/) as the reference for structure, layout,
motion, mobile behaviour, menus and popups, and
[Harness Developer Hub](https://developer.harness.io/artifact-registry/use-artifact-registry/manage-registries)
as the reference for documentation. Both are to be matched as closely as possible, with Verity's own
brand, copy, data and visuals. Their content, logos and artwork are not copied.

## What changes

- **Snapshot first.** The site as it stood is tagged `website-v1` at `931b924`. The older archive
  that commit called "v1" is renamed `website-v0-source-2026-10-01.zip`, so the names follow the
  order the designs were made in.
- **A new public design system** that follows the reference: serif display headings, Inter body text,
  monospace eyebrow labels, a light cool-grey hero, a black and white button pair, thin framed
  section rules, floating product-interface cards, code-native charts, and scroll-led motion that
  stops entirely for visitors who prefer reduced motion.
- **The full platform story.** Every module, live or planned, appears in the navigation, the pages
  and the documentation. Anything not generally available carries a visible **Coming soon** badge,
  and its documentation page opens with a banner saying so. Two sources feed the list: the delivery
  plan's Phase 2 and 3 work, and the product owner's additions (Trust Center, security questionnaire
  automation, security awareness training, device monitoring, SOC 1 and SOC 3 support, and an AI
  assistant).
- **Information architecture.** Home, a platform overview and one page per module, five industry
  pages, a framework library filterable by region, category and status, Why Verity, Pricing (plan
  tiers with no prices and a Talk to sales path), Security, a demo request page, and the
  documentation portal.
- **Website-owned documentation.** MDX under `website/content/docs/`, seeded from
  `docs/user-guide/` but restructured into task-based pages. The docs shell follows the reference:
  top bar, collapsible sidebar, breadcrumbs, scroll-tracked contents, ⌘K search, light and dark
  themes, previous and next links. Pages use interactive components (steps, tabs, callouts,
  lifecycle diagrams, zoomable screenshots, numbered screenshot walkthroughs) and fresh high-density
  screenshots captured from the running application with demonstration data. `docs/user-guide/` stays
  in the repository, untouched, and stops being a build input.
- **Demo requests** open as a popup from every "See a demo" and "Talk to sales" action, and on
  `/demo/`. The form posts to an HTTPS endpoint set at build time. Until one is configured, submit
  stays disabled and the form says plainly that nothing is sent.
- **English only, ready for more.** Copy lives in content modules rather than scattered through
  components, and layout uses CSS logical properties, so Arabic (right to left) and Urdu can be
  added without a redesign.

## What does not change

- No platform code, schema, API, authentication, RBAC, tenancy, audit trail, migration or
  append-only table changes. `main` is read-only for this work. Only the website branch changes.
- No invented customers, logos, testimonials, usage metrics, certifications or prices. Proof comes
  from facts about the shipped content library (61 SOC 2 criteria, 114 control templates, 15 policy
  templates, 60 library risks, 59 vendor questionnaire questions) and from how the product is built.
- Verity is presented as software only. No consulting, vCISO, audit or managed services are
  marketed.
- No region landing pages, regulator supervisory offering, deployment-option claims (such as
  on-premises), analytics, cookies or third-party scripts.

## Decisions recorded with the product owner (2026-10-02)

| Question | Decision |
|---|---|
| Where the work lands | Commit directly to `codex/public-website`. `main` is never written. |
| How the current site is saved | Git tag `website-v1` on the current website commit. The older zip is renamed v0. |
| Features that are not built yet | Show everything, with a visible Coming soon badge on unbuilt items. |
| "Compliance as a service" | Software platform only. No human services marketed. |
| Market-specific pages | Industry pages only (banking and financial services, fintech and payments, healthcare, SaaS and technology, government and public sector). |
| Documentation source | Website-owned MDX, restructured, with Coming soon pages and fresh screenshots. |
| Pricing | Plan tiers, Talk to sales, no prices. |
| Spec flow | Write this change first, then build. Review everything together. |
| Languages | English only at launch, structured for later localisation. |
| Demo form | Posts to a build-time configured endpoint. Disabled with a notice until configured. |
| Proof | No customers to show yet. Use honest product facts. |
| Out-of-plan extras | Trust Center, questionnaire automation, security awareness training, device monitoring, SOC 1 and SOC 3, and an AI assistant all appear as Coming soon. |

## Relationship to `add-public-website`

This change supersedes the homepage, navigation and documentation presentation requirements of
`add-public-website`. It keeps that change's static-export architecture, origin validation, security
headers and no-tracking posture. Archive `add-public-website` first, then this change.

## Impact

- `website/` is rebuilt. `website/lib/guide.ts` and `scripts/prepare-guide.ts` are replaced by the
  MDX content pipeline.
- New website dependencies, each with its reason in `design.md`: `@mdx-js/mdx` and `yaml` for
  documentation, `@fontsource-variable/source-serif-4` and `@fontsource-variable/jetbrains-mono`
  for the type system. `react-markdown` and its plugins, `@fontsource/sora`, `github-slugger` and
  `mdast-util-to-string` go once nothing uses them.
- Hosting: the same static export. If a demo endpoint is configured, the host's CSP `connect-src`
  must include its origin.
- Review flags: none of tenant isolation, authentication, authorization, audit trail, database
  relationships, migrations or append-only tables is touched.
