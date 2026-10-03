# Public Verity website and user documentation

## Why

Verity needs a credible public entry point for B2B buyers and a usable, searchable home for its existing end-user guide. Today the product frontend is an authenticated application, and the guide lives only as repository Markdown and a generated HTML file. Buyers need a clear path to trial or demo; customers need task-oriented help that is readable without an account.

This is a **public-site deliverable alongside the current platform**, not a Phase 2 or 3 product feature. It packages and accurately explains shipped capabilities without changing the product roadmap.

## What changes

- Add a separate `website/` React + TypeScript + Tailwind application with a polished, responsive, accessible marketing homepage and a public documentation area.
- Publish the complete `docs/user-guide/` Markdown collection (README plus 13 chapters) and its 43 screenshots from those source files, with search, navigation, and working deep links.
- Show both **Start trial** and **Book a demo** actions. Trial and sign-in link to the existing application at `https://runwaydream.com` using its verified local `/sign-up` and `/sign-in` routes. The demo action opens a public form with a preferred-date calendar. Submission remains disabled until a booking service and privacy handling are approved and connected.
- Ship static, crawlable pages with metadata, sitemap, robots policy, image optimization, security headers at the host, and a documented build/deploy process.
- Use original Verity visual assets and honest product copy. Do not publish the temporary Vimeo app mark or describe preview/planned features as live.

## Experience direction

For buyers: a general GRC and security platform proposition, a clear view of the control-to-evidence relationship, concrete product capabilities, security/accountability detail, self-service documentation, and repeated trial/demo choices. Use a light enterprise layout, strong typography, original code-native product examples, and generous hierarchy. Keep product screenshots in the guide rather than presenting raw application captures on the homepage. Avoid generic compliance badges, invented customer logos, invented metrics, and borrowed competitor artwork.

For end users: a task-oriented guide entrance, persistent chapter navigation, search, breadcrumbs, on-page contents for long chapters, previous/next links, readable screenshots, and the guide's existing preview/Soon/demo-data disclosures. The docs should remain useful on a narrow screen and with keyboard or screen reader navigation.

Inspiration is organizational and interaction-level: [Harness's light hero, platform menu, and product sections](https://www.harness.io/), [Harness's task-based documentation](https://developer.harness.io/artifact-registry/use-artifact-registry/manage-registries), [Vanta's platform explanation](https://www.vanta.com/), [Drata's product narrative](https://drata.com/), and [Byro's editorial page rhythm](https://byro.ee/). Do not copy their content, visual assets, or brand identity.

## Non-goals

- No changes to authenticated frontend, backend, APIs, database, auth, RBAC, tenant isolation, audit trail, or append-only tables.
- No new trial signup flow, CRM integration, live lead submission, documentation CMS, chatbot, analytics service, or private documentation access.
- No claim of SOC 2 certification, full continuous monitoring, broad connector coverage, or other unverified/roadmap features.
- No legal/privacy/terms text invented for the public site; link only to approved policies once supplied.
- No deployment to a live domain as part of this change; publishing needs the real site domain, verification of the app destination, and a connected booking service.

## Modules and review flags

New module: standalone `website/`. Read-only build input: `docs/user-guide/` and optional approved brand tokens. Existing backend and authenticated frontend modules are untouched. No platform module boundary is crossed. This change does **not** touch tenant isolation, authentication, authorization, audit trails, database relationships, migrations, or append-only tables. Public documentation must contain no tenant data or secrets; the screenshots are from a demonstration workspace and must retain that label.
