# Frontend — conventions for AI-assisted work

React 18 + TypeScript (strict) + Tailwind + Vite. TanStack Query for server state.
The cross-cutting quality bar (SOLID, reuse, component design) is
[../docs/conventions/code-quality.md](../docs/conventions/code-quality.md) — read it alongside this.

## Layout

```
src/
  app/               routes and layouts only
  features/<name>/   mirrors a backend module one-for-one
    api.ts           typed calls for this feature
    components/      feature-owned components
    hooks/           feature-owned hooks
    types.ts         types derived from the API contract
  components/ui/     design-system primitives ONLY (Button, Input, Dialog, Table)
  lib/               api client, auth, query config, formatters
  hooks/             genuinely cross-feature hooks
```

**Rule:** a component used by one feature lives in that feature. `components/ui/` is for
primitives with no domain knowledge. A `VendorTierBadge` in `components/ui/` is a mistake.

Features do not import from each other. Shared domain concepts move to `lib/` or get lifted into
a route composition in `app/`.

## Types

- `strict: true`. **No `any`.** If a type is genuinely unknown, use `unknown` and narrow.
- API types are generated from the backend OpenAPI schema, not hand-written. Hand-written types
  drift and the drift is silent.
- No non-null assertions (`!`) to silence the compiler. Handle the null.

## Server state

- All server data goes through TanStack Query. Never `useEffect` + `fetch` + `useState`.
- Query keys are structured and include tenant scope: `['vendors', tenantId, filters]`.
- Mutations invalidate precisely — not the whole cache.
- Loading, empty, and error states are **required** for every data view. An unhandled error state
  is an incomplete feature, not a follow-up ticket.

## Components

- Server state and business rules do not live in components. Components render.
- Prefer composition over configuration: a component with more than ~6 props usually wants to be
  split or take `children`.
- Forms use React Hook Form + Zod, with the Zod schema mirroring the backend's validation. The
  backend still validates everything — client validation is UX, never a security control.

## Tailwind

- Use design tokens from the config (spacing, colour, radius scale). No arbitrary values like
  `w-[327px]` outside genuinely one-off layout.
- Tenant branding (logo, colours, custom domain) is **runtime data from the tenant, not build-time
  config**. Theme through CSS custom properties set from the tenant's branding record. The platform
  is white-label; hardcoding brand colours breaks that.
- Repeating class strings become a component, not a copy-paste.

## Accessibility

Non-negotiable, and this is an enterprise product that will be procurement-reviewed:
keyboard reachable, labelled inputs, visible focus, semantic elements, dialogs that trap focus and
restore it on close. Use headless primitives (Radix) rather than reimplementing them.

## Security

- Never render untrusted HTML. Rich-text document content is sanitised **server-side** before it
  is stored, and the client still treats it as untrusted.
- No tokens in `localStorage`. Phase 1 auth is native (session/token) behind the app's identity seam; an external OIDC IdP federates in later. Tokens are held per the auth strategy in
  [../docs/adr/0006-keycloak-as-identity-provider.md](../docs/adr/0006-keycloak-as-identity-provider.md).
- The UI hides what a user cannot do, and the **backend enforces it**. A hidden button is not a
  permission check.
- Nothing sensitive in URLs or query strings.

## Testing

- Vitest + Testing Library. Test behaviour through the DOM, not implementation details.
- Playwright for the critical journeys: login, evidence upload and mapping, control pass/fail,
  approval flow, and the 360° trace.
- Query by role and label, not by test id, unless there is no accessible alternative.
