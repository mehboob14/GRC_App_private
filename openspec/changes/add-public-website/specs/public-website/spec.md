# Public website

## ADDED Requirements

### Requirement: Buyer-facing pages explain Verity accurately

The public homepage SHALL explain Verity as a governance, risk, and compliance workspace in concrete language, including controls, evidence, assets, vulnerability findings, and third-party risk. It SHALL distinguish the shipped SOC 2 content library from planned framework libraries and business continuity workflows, and identify VantageMDM as separate software. It SHALL offer visible trial and demo actions. Its opening SHALL be a short white, skippable introduction that plays once per browser session and is omitted for reduced-motion visitors. The hero SHALL use an original code-native relationship illustration; the product views SHALL be original illustrative compositions. Light editorial sections SHALL show control ownership, evidence review, risk, asset management, vulnerability management, vendor engagements, and accountability through views that respond to scrolling or direct visitor input. These views SHALL remain legible without animation and SHALL not present invented customer metrics or claim that planned features are live. Raw application screenshots, decorative arrows, generic audience strips, empty slogans, and unsupported proof claims SHALL not be used on the homepage.

#### Scenario: Buyer evaluates the platform

- **GIVEN** a visitor opens the homepage on a desktop or mobile device
- **WHEN** the page loads
- **THEN** they can understand the core control/evidence workflow and the current asset, vulnerability, vendor, and risk areas without signing in
- **AND** they can reach both trial and demo actions from the page
- **AND** they can distinguish current SOC 2 content from planned additional framework libraries

#### Scenario: Visitor explores the product story

- **GIVEN** a visitor scrolls through the homepage or selects a product example
- **WHEN** they encounter the compliance, security, vendor, or relationship examples
- **THEN** the accompanying text names the workflow the view represents
- **AND** keyboard users can select relationship examples without depending on scroll position
- **AND** reduced-motion visitors can read and use the same content without movement

#### Scenario: Visitor examines operational coverage

- **GIVEN** a visitor reaches a product section or the relationship map
- **WHEN** they read the original sample record or select a map topic
- **THEN** the relevant owner, record, or decision relationship appears with a guide link where appropriate
- **AND** map topics can be selected with a keyboard

#### Scenario: Visitor reaches the homepage

- **GIVEN** a first visit in this browser session
- **WHEN** the homepage opens
- **THEN** a short white Verity introduction appears
- **AND** the visitor can skip it immediately or wait for the hero to appear
- **AND** subsequent visits in the session and reduced-motion visits open the hero directly

#### Scenario: Destination configuration is missing

- **GIVEN** a production build lacks a valid public site origin or app/signup destination
- **WHEN** the production build runs
- **THEN** the build fails with a clear configuration error rather than publishing a broken or placeholder CTA

#### Scenario: Visitor opens a demo request

- **GIVEN** a visitor selects Book a demo
- **WHEN** the homepage demo section or direct `/demo/` route loads
- **THEN** they see a short form, a calendar for a preferred date, and a preferred time window
- **AND** the page clearly distinguishes a preference from a confirmed appointment
- **AND** until a reviewed booking service is connected, submission is disabled and no personal data is sent

#### Scenario: A capability is not yet live

- **GIVEN** a capability is documented as preview, Soon, or planned in the application or user guide
- **WHEN** it appears in public marketing copy
- **THEN** the copy labels that status clearly or omits the claim

### Requirement: The complete existing guide is public and navigable

The documentation area SHALL render `docs/user-guide/README.md` and every numbered chapter from the repository source, including all referenced images, tables, lists, headings, and notes. It SHALL preserve meaningful URL fragments and internal chapter navigation and SHALL not expose files outside the approved guide tree.

#### Scenario: Reader follows a walkthrough

- **GIVEN** a reader enters the guide index
- **WHEN** they choose a chapter, follow an in-guide link, or use previous/next navigation
- **THEN** the expected guide content and screenshot appear at a stable public URL
- **AND** the reader can navigate back to the guide index and other chapters

#### Scenario: Reader arrives from search or a shared link

- **GIVEN** a valid chapter URL with a heading fragment
- **WHEN** the page is loaded directly
- **THEN** server-generated HTML contains the chapter, title, and content and the fragment targets the intended heading

#### Scenario: An invalid documentation URL is requested

- **GIVEN** an unknown chapter slug or a path attempting to escape the guide directory
- **WHEN** it is requested
- **THEN** the site returns its public not-found response and exposes no repository file contents

#### Scenario: Source content is broken

- **GIVEN** a guide Markdown file references a missing local chapter, fragment, or image
- **WHEN** documentation validation/build runs
- **THEN** the build fails and identifies the source file and broken reference

### Requirement: Documentation discovery serves real user tasks

The docs area SHALL offer text search across all published guide chapters and task/role entry points based on the guide README. Search SHALL be usable by keyboard and SHALL provide a clear empty-result state.

#### Scenario: Reader searches for a task

- **GIVEN** a reader enters a term that appears in a chapter heading or body
- **WHEN** search results appear
- **THEN** each result identifies the chapter, relevant heading or excerpt, and a working destination

#### Scenario: Search yields nothing

- **GIVEN** a term absent from the guide
- **WHEN** search completes
- **THEN** the reader sees a no-results message and a way to return to the chapter index

### Requirement: Public pages meet launch quality gates

The site SHALL provide semantic structure, visible focus, keyboard-operable navigation/search, appropriate image alt text, reduced-motion behavior, mobile layouts, crawlable HTML, unique page titles/descriptions, canonical URLs, and an indexable sitemap. It SHALL avoid shipping third-party trackers or remote runtime dependencies by default.

#### Scenario: Assistive technology or keyboard use

- **GIVEN** a visitor uses only a keyboard or screen reader
- **WHEN** they navigate the homepage or docs
- **THEN** menus, links, search, headings, skip link, and screenshot alternatives remain usable and understandable

#### Scenario: Slow or unavailable app destination

- **GIVEN** the app signup site is unavailable
- **WHEN** a visitor uses a CTA
- **THEN** the public site itself remains readable and the trial CTA remains an ordinary link with an understandable destination; it does not make a blocking runtime API call

#### Scenario: Public access

- **GIVEN** a visitor has no Verity session
- **WHEN** they open any marketing or guide page
- **THEN** it renders without authentication, tenant context, or platform permission checks

No new platform routes or permission keys are added. Object-scoped filtering and audit writes do not apply because the public site is read-only static content. The authenticated application remains responsible for all state changes.
