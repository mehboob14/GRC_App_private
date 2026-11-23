---
name: verity-website-deploy
description: "Public website runs as its own container on the Contabo server and is live at the temporary sslip.io address; branch feat/website-deploy, edge handled by a root-run script, what is committed and what is still pending"
metadata:
  node_type: memory
  type: project
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-06T14:43:53.944Z
---

`website/` (Next.js static export) is served by container `verity-site` (compose project `verity-site`, own network `verity-site_default`, nothing published), live at `https://website.37-60-228-227.sslip.io` as of 2026-10-06 (the user showed the docs there). Files: `website/Dockerfile`, `infra/docker/docker-compose.website.yml`, `infra/docker/.env.website.example`, `infra/docker/edge-nginx-website.conf.template`, `infra/scripts/deploy-site.sh`, `infra/scripts/edge-add-website.sh`, `docs/runbooks/website.md`.

**Server layout:** the user has no sudo, so the site is a detached git worktree at `~/verity-site` of the `/opt/verity` repo (`git worktree add --detach ~/verity-site origin/feat/website-deploy`), settings in `infra/docker/.env.website`, updates with `git fetch` in `/opt/verity`, `git checkout --detach origin/feat/website-deploy` in the worktree, `bash infra/scripts/deploy-site.sh`. The edge nginx container `keycloak-nginx` (with `keycloak-certbot`) belongs to the Keycloak stack under `/root/keycloak-saml`, mounted read-only, root only: `edge-add-website.sh [hostname]` (run by whoever has root) issues the certificate, installs `sites-enabled/website` from the template, runs `nginx -t` first and undoes itself on failure. Final hostname later: one A record at GoDaddy, then that script with the new name, `SITE_URL` changed, rebuild.

**Branch state 2026-10-06:** `feat/website-deploy` is pushed through `33df557`: the new homepage hero copy ("Compliance without the scramble."), the `/demo/` request page, and the docs defaults (docs white unless the reader chose dark, sidebar sections closed with a dot on the section holding the current page). Pushed, not yet deployed to the server: the user has to run the platform deploy first, then `deploy-site.sh`. Built in the scratch copy `scratchpad/site-work` and committed by `site_sync_commit.py plan|commit|push`. See [[verity-demo-request-flow]].

**Why the plumbing:** the checkout is on `codex/public-website` with another tool running in it, so commits are built through a temporary index and the checkout is never touched. The user's local checkout therefore does not show these website changes until the branch is merged.

Local gotchas: Windows docker and WSL docker are different daemons, run WSL commands as `MSYS_NO_PATHCONV=1 wsl bash /mnt/c/...`. Related: [[verity-deploy-runbook]], [[deploy-and-client-comms-style]], [[feedback-backslashes-in-bash-python]].

**Local run (2026-10-16):** the `website/` on disk in the main checkout is Codex's older, uncommitted version (leave alone). The latest site (`feat/website-deploy`, 33df557) runs from a separate git worktree at `C:\Development\Verity_site` (own `npm ci`; a junction to the other node_modules makes Turbopack panic). Start it with `preview_start verity-site` (entry added to `grc-s/.claude/launch.json`, port 3001). Edits belong in that worktree, then commit to `feat/website-deploy` by explicit path.
