# Verity public website

Standalone React/Next.js + Tailwind site for buyers and end users. It is independent of the authenticated `frontend/` and has no product API, database, or tenant context. Its public guide is built from `../docs/user-guide/README.md`, the 13 chapter Markdown files, and their images. Edit those source files; do not edit generated files under `public/guide-images/` or `public/guide-search.json`.

The homepage uses original HTML/CSS sample workspace views and a code-native relationship diagram for controls, evidence, assets, vulnerabilities, risk, and vendor engagements. They are illustrative records, not captured product screens or live metrics. Keep their wording aligned with current product workflows; use the guide's real screenshots for end-user instructions. The shipped framework library is SOC 2 today; additional libraries and business continuity workflows remain planned. VantageMDM is separate software, not a Verity integration. The source-only v1 snapshot is saved at `../website-v1-source-2026-10-01.zip`.

## Local development

Use Node 22 or later. From `website/`:

```powershell
npm ci
npm run dev
```

Open <http://localhost:3001>. Trial and sign-in point to the user-provided `https://runwaydream.com` app origin by default. Set `APP_URL` for a staging app.

## Production build

Set these build-time values to real approved destinations:

| Variable | Purpose |
|---|---|
| `SITE_URL` | Canonical HTTPS origin of this public site |
| `APP_URL` | HTTPS origin of the existing Verity app; defaults to `https://runwaydream.com`; trial and sign-in use `/sign-up` and `/sign-in` |

`.env.example` shows the shape only; its example site domain must never be used for a release. Then:

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

`npm run build` fails if a required production URL is absent or invalid. It validates Markdown links, heading fragments, image references, and alt text; generates branded copies of the 43 guide screenshots; builds search data; and exports static pages to `out/`. Serve **only** `out/`. The repository root must remain available at build time because `website/` reads `../docs/user-guide/`.

## Hosting

Deploy `out/` as a static site on its own origin, separate from the app. The included [nginx.conf](nginx.conf) is a host example: configure HTTPS and HSTS at the TLS edge, preserve clean `/docs/.../` paths, serve `404.html` for unknown routes, and apply the declared security headers. A CDN/static host is equally suitable if it implements the same behavior. Check response headers after deployment and confirm direct chapter links, `/sitemap.xml`, `/robots.txt`, `/guide-search.json`, and screenshot URLs. No runtime Node process is required.

The CSP permits inline script and style because Next's static export emits inline hydration data and CSS. It blocks third-party script, frames, and network calls. Revisit the policy if the framework output changes; do not add external analytics or embeds without a privacy and CSP review.

## Demo request status

The homepage embeds the demo form and preferred-date calendar at `/#request-demo`; `/demo/` retains a direct route to the same interface. Neither form submits or reserves a time because no booking service or receiving inbox has been provided. The button is disabled and both pages say that no information is sent. Before public launch, connect a reviewed booking service, confirm actual slot availability and response handling, add an approved privacy notice and abuse controls, and test end-to-end delivery. Keep the distinction between a preferred date and a confirmed appointment.

## Content and brand review before publication

- Check every public capability statement against current implementation. The Dashboard remains a preview, GitHub is the first live connector, and the guide's “Soon” screens are not live.
- Keep the guide's demonstration-data and preview disclosures visible.
- The product's current `frontend/public/brand/app-mark.png` is explicitly documented as a temporary Vimeo mark. The website build replaces the small mark region in generated screenshot copies with its original Verity mark, leaving source guide images untouched. Visually review generated copies before public launch and replace the source captures when the product has its final approved brand.
- Provide the actual public site origin. `https://runwaydream.com/sign-up` and `/sign-in` were verified as Verity app pages on 2026-10-01; recheck before publishing. Connect demo booking before publishing; add legal/privacy links only to approved published policies.

The website is specified in `openspec/changes/add-public-website/`.
