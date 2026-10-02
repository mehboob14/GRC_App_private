# Tasks: public website and documentation revamp

Each task fits within about two hours. Check a task off only when it is verified.

- [x] 1. Tag the site as it stood as `website-v1` (`931b924`) and rename the older archive to `website-v0-source-2026-10-01.zip`.
- [x] 2. Write this change: proposal with recorded decisions, design with per-section reasoning, spec deltas, tasks.
- [ ] 3. Add dependencies with stated reasons; remove packages nothing uses; keep the lockfile pinned.
- [ ] 4. Build the content catalog (`content/catalog.ts`): modules, capabilities, integrations and frameworks with `live`/`preview`/`soon` status; derive navigation from it.
- [ ] 5. Build the visual system: tokens, type, buttons, eyebrow, section frame, chips, status badges, cards, reveal-on-scroll hook, reduced-motion handling.
- [ ] 6. Build the header with Platform, Solutions and Resources mega menus, the mobile drawer, and the footer.
- [ ] 7. Build the demo request popup and `/demo/` page with the configured endpoint, honeypot, minimum fill time, preselected interests, and success, error and disabled states.
- [ ] 8. Build the code-native product compositions: flow steps, status and severity pills, tables, donut, bar, stacked bar, gauge, heat map, chat and assistant response, KPI tiles.
- [ ] 9. Build the animated isometric hero illustration with a static reduced-motion state.
- [ ] 10. Build the homepage sections in the order and with the reasoning in `design.md`.
- [ ] 11. Build the platform overview and the module page template (live and coming-soon variants); write all 18 module pages.
- [ ] 12. Build the industry page template and write the five industry pages from verified regulatory research.
- [ ] 13. Build the framework library with filters, search and the details popup.
- [ ] 14. Build Pricing, Why Verity and Security pages.
- [ ] 15. Build the MDX pipeline with validation; the docs shell (top bar, sidebar, breadcrumbs, contents rail, theme, previous/next, feedback); and the MDX components.
- [ ] 16. Build the docs search index and the ⌘K search modal.
- [ ] 17. Migrate and restructure the guide into task-based MDX pages; write the coming-soon and reference pages; add redirect stubs for old chapter URLs.
- [ ] 18. Capture fresh 2x screenshots from the running application with demonstration data; optimise them; record element boxes; wire walkthrough hotspots.
- [ ] 19. Update metadata, sitemap, robots, the social image, the 404 page, the `nginx.conf` CSP note and `website/README.md`.
- [ ] 20. Verify: typecheck, lint, tests, production build, route smoke tests, Playwright review at 1440 and 390 widths, keyboard, reduced motion, copy review of every Live claim and every Coming soon badge. Fix findings in this change.
- [ ] 21. Product-owner follow-ups (not blocking the build): prices, tier packaging confirmation, legal pages, company contact details, demo and feedback endpoints, public domain.
