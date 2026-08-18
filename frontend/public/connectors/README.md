# Connector logos

Vendor marks shown on `/connectors`. Used nominatively — to identify which
integration a card is for — which is what every integration directory does.
They are **not** Verity assets; each mark remains the trademark of its owner.

## Provenance

| Source | Files | Notes |
|---|---|---|
| The client's Figma integration-logo set | the original 22 | Exported by the design team. Identifiable by `preserveAspectRatio="none"` and Figma layer ids. |
| [github.com/gilbarbara/logos](https://github.com/gilbarbara/logos) | `digitalocean`, `heroku`, `jenkins`, `teams` | Fetched 2026-08-18. Repo is CC0; the marks themselves are not. `digitalocean` and `heroku` are the `-icon` variants — the plain files there are wide wordmarks that render illegibly at 48px. |

Every fetched file was scanned for active content (`<script>`, `on*=` handlers,
`<foreignObject>`, `<iframe>`, external `href`) before being committed. These
are served same-origin from `public/`, so an SVG carrying script would run
against a signed-in session. **Scan anything you add here.**

Fetched files are normalised: root `width`/`height` stripped so the `viewBox`
drives sizing, `preserveAspectRatio="xMidYMid meet"` so a non-square mark
letterboxes instead of distorting.

## Still missing (14 of 40)

`bamboohr` `crowdstrike` `duo` `entra` `gusto` `intune` `jamf` `jumpcloud`
`kandji` `onelogin` `rippling` `sentinelone` `servicenow` `workday`

Not available from any redistributable source. Several — CrowdStrike,
ServiceNow, Workday, Jamf — are absent from the public icon sets precisely
because those vendors enforce their marks, so scraping them is the wrong move.
`gusto` exists only as a 2.6:1 wordmark that renders ~12px tall in a 48px tile.

To add one: get the SVG from the vendor's own brand/press kit (most publish
one), scan it, normalise it, and drop it in as `<connector-id>.svg`.
`ConnectorLogo` picks it up with no code change; until then those cards fall
back to the vendor's initials, which is honest rather than wrong.

Do **not** hand-draw a substitute. An invented mark that looks like a vendor's
is worse than initials.
