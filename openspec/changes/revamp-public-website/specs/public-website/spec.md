# Public website

## MODIFIED Requirements

### Requirement: Buyer-facing pages explain Verity accurately

The public site SHALL present Verity as one compliance and security platform covering compliance,
evidence, policies, risk, third-party risk, assets, vulnerabilities, integrations, workflows and
governance, including the modules and framework libraries that are not yet available. Every item
that is not generally available SHALL carry a visible Coming soon badge wherever it appears. An item
shown as preview SHALL be labelled Preview. Items SHALL take their status from one catalog, so no two
pages disagree. The site SHALL NOT present invented customers, logos, testimonials, usage metrics,
certifications or prices, and SHALL NOT market human services. Proof SHALL come from verifiable
product facts. Product visuals SHALL be original code-native compositions or screenshots of the
application with demonstration data, labelled as such.

#### Scenario: Buyer evaluates the platform

- **GIVEN** a visitor opens the homepage on a desktop or mobile device
- **WHEN** they scroll the page
- **THEN** they can tell what Verity is, who it is for and what it does from the hero alone
- **AND** they can reach See a demo and Start trial from the header, the hero and the closing section
- **AND** each pillar section names a job, shows a product composition and links to its module page

#### Scenario: A capability is not yet live

- **GIVEN** a module, capability, integration or framework whose catalog status is `soon`
- **WHEN** it appears in a menu, chip, card, table, library entry, docs sidebar or page
- **THEN** it shows a Coming soon badge that is announced as text to assistive technology
- **AND** its own page, if it has one, opens with a banner naming what is available today instead
- **AND** its copy describes what it will do without dates, numbers or usage claims

#### Scenario: A status changes

- **GIVEN** an item's status changes from `soon` to `live` in the catalog
- **WHEN** the site is rebuilt
- **THEN** every badge, table cell, filter result and docs entry for that item updates together

### Requirement: Documentation discovery serves real user tasks

The docs SHALL offer search across every documentation page from a ⌘K/Ctrl+K/"/" modal, ranking
title and heading matches first. Results SHALL be section-level, with highlighted excerpts, and SHALL
be fully keyboard operable, with a clear empty state. The docs home SHALL offer role and task entry
points.

#### Scenario: Reader searches for a task

- **GIVEN** a reader presses ⌘K and types a term found in a heading
- **WHEN** results appear
- **THEN** the heading's section is ranked first, and Enter opens the page at that heading

#### Scenario: Search yields nothing

- **GIVEN** a term absent from the docs
- **WHEN** search completes
- **THEN** the reader sees a no-results message with a link to the documentation home

### Requirement: Public pages meet launch quality gates

The site SHALL provide semantic structure, visible focus, keyboard-operable menus, dialogs, search,
tabs and walkthroughs, alt text, reduced-motion behaviour, mobile layouts without horizontal scroll,
light and dark documentation themes, crawlable static HTML, unique titles and descriptions,
canonical URLs and a sitemap. It SHALL ship no third-party trackers, cookies or remote runtime
dependencies.

#### Scenario: Keyboard-only visitor

- **GIVEN** a visitor using only a keyboard
- **WHEN** they move through the header, a mega menu, the demo popup, the docs search and a walkthrough
- **THEN** every control is reachable, operable and visibly focused, and Escape always retreats one level

## ADDED Requirements

### Requirement: The site matches the reference experience

The site SHALL follow the structure and behaviour of the named reference site. It SHALL have a
persistent header with Platform, Solutions and Resources mega menus, Why Verity and Pricing links,
and Sign in, See a demo and Start trial actions. It SHALL have a light hero with a serif headline and
an original animated isometric illustration, a stat strip, alternating pillar sections with
product-interface compositions and capability chips, and a multi-column footer. On narrow screens the
navigation SHALL collapse into a full-height drawer with expandable groups, and every page SHALL
render without horizontal scrolling at 360px.

#### Scenario: Visitor opens a mega menu

- **GIVEN** a desktop visitor
- **WHEN** they hover (fine pointer) or activate (keyboard or touch) the Platform menu
- **THEN** a panel shows the modules in their groups, each with an icon, a description and any status badge
- **AND** Escape, clicking outside or moving to another menu closes it, returning focus to its trigger when keyboard-opened

#### Scenario: Visitor uses a phone

- **GIVEN** a viewport 390px wide
- **WHEN** the visitor opens the menu button
- **THEN** a drawer lists every group with expandable sections and the demo and trial actions
- **AND** body scrolling is locked until the drawer closes

### Requirement: Motion is purposeful and optional

Reveal, chart, flow and hero animations SHALL run only when the visitor has not requested reduced
motion. With reduced motion requested, every element SHALL render in its final state, and no
information SHALL depend on animation.

#### Scenario: Reduced motion

- **GIVEN** a visitor whose system requests reduced motion
- **WHEN** any page loads and scrolls
- **THEN** no element animates, and all charts, flows and illustrations show their final state

### Requirement: Module, industry and framework pages

The site SHALL have a platform overview, one page per module in the catalog, five industry pages
(banking and financial services, fintech and payments, healthcare, SaaS and technology, government
and public sector), and a framework library. The library SHALL be filterable by region, category,
status and text, and SHALL show each framework's issuer, version, scope, audience and status in a
details popup. Industry pages SHALL name obligations and frameworks only in verified terms.

#### Scenario: Bank evaluator checks regulatory coverage

- **GIVEN** a visitor on the framework library
- **WHEN** they filter by region Pakistan
- **THEN** they see the State Bank of Pakistan frameworks in the catalog, each with its status
- **AND** opening one shows its issuer and version and states that Verity prepares the work while certification or attestation comes from an auditor or certification body

### Requirement: Pricing without prices

The pricing page SHALL show plan tiers with descriptions and a comparison table that marks each
capability as included, coming soon or not included. It SHALL show no prices or currencies. Each
tier's action SHALL open the demo request with that tier preselected.

#### Scenario: Visitor compares plans

- **GIVEN** a visitor on the pricing page
- **WHEN** they read the comparison table on desktop or mobile
- **THEN** every row is readable without horizontal page scrolling, and Coming soon cells are labelled in text

### Requirement: Demo requests use a configured endpoint

See a demo, Talk to sales and module interest actions SHALL open an accessible demo request popup.
`/demo/` SHALL render the same form. The form SHALL submit JSON only to the HTTPS endpoint set at
build time, without cookies. It SHALL use a honeypot and a minimum fill time, and SHALL show success
and error states. With no endpoint configured, submit SHALL be disabled and the form SHALL state that
nothing is sent.

#### Scenario: Endpoint configured

- **GIVEN** a build with a valid HTTPS demo endpoint
- **WHEN** a visitor completes the required fields and submits
- **THEN** the form posts once, shows a success state on a 2xx response, and offers a retry on any other response

#### Scenario: Endpoint not configured

- **GIVEN** a build without a demo endpoint
- **WHEN** a visitor opens the form
- **THEN** the submit button is disabled and the form says that requests are not being sent yet

#### Scenario: Popup accessibility

- **GIVEN** the popup is open
- **WHEN** the visitor tabs or presses Escape
- **THEN** focus stays inside the popup, Escape closes it, and focus returns to the action that opened it

### Requirement: Documentation is website-owned, task-based and validated

The documentation SHALL be authored as MDX under `website/content/docs/`, ordered by a navigation
file, and grouped by task. It SHALL include pages for coming-soon features, marked with a badge and
banner. Pages SHALL support callouts, steps, tabs, zoomable screenshots, hotspot walkthroughs,
lifecycle diagrams and cards. The build SHALL fail, naming the file and reference, on any broken
internal link or fragment, missing image, missing alt text, invalid front matter, unknown component,
or page absent from the navigation.

#### Scenario: Reader follows a walkthrough

- **GIVEN** a reader on a documentation page with a hotspot walkthrough
- **WHEN** they step through it with the buttons or arrow keys
- **THEN** each numbered hotspot highlights the named interface element on the screenshot, with its instruction

#### Scenario: Broken reference

- **GIVEN** an MDX page that links to a missing page or heading
- **WHEN** the site builds
- **THEN** the build fails and names the file and the broken reference

### Requirement: Internationalisation readiness

Marketing copy SHALL live in content modules rather than inline across components. Layout SHALL use
logical CSS properties, and the document language and direction SHALL come from configuration, so a
right-to-left locale can be added without restructuring pages.

#### Scenario: A locale is added later

- **GIVEN** a translated content module and `dir="rtl"`
- **WHEN** pages render
- **THEN** layout mirrors through logical properties without per-component overrides

### Requirement: Versions are recoverable

Before a redesign replaces the site, the previous version SHALL be recoverable from version control
under a named reference: the `website-v1` tag for the version this change replaces.

#### Scenario: Restoring v1

- **GIVEN** the repository
- **WHEN** someone checks out `website/` from `website-v1`
- **THEN** they get the previous site source, buildable with its own lockfile

## REMOVED Requirements

### Requirement: The complete existing guide is public and navigable

**Reason:** documentation is now website-owned MDX, restructured into task-based pages with
interactive components. `docs/user-guide/` stays in the repository but is no longer a build input.

**Migration:** every chapter's content is carried into the new pages. Deep links to old
`/docs/NN-chapter/` URLs are covered by redirect stubs to their new pages.
