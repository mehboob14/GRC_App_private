# Public website

The public site (`website/`, a Next.js static export) runs on the same server as the platform
but as its own compose project, `verity-site`: one nginx container serving files that were
built into its image. No database, no secrets, no Node at runtime. It shares no network with
the platform, so a bad site deploy cannot reach the app.

| | |
|---|---|
| Container | `verity-site` (nginx, port 80 inside, nothing published) |
| Compose | `infra/docker/docker-compose.website.yml`, settings in `infra/docker/.env.website` (per server, not committed) |
| Checkout | `/opt/verity-site`, a detached git worktree of the platform repository, so the platform's own checkout stays on its branch |
| Address | `SITE_URL` in the settings file. Temporary: `https://website.37-60-228-227.sslip.io` |
| HTTPS | ends at the edge nginx (`keycloak-nginx`), which proxies to `verity-site` |

## First time

```bash
sudo mkdir -p /opt/verity-site && sudo chown "$USER": /opt/verity-site
cd /opt/verity && git fetch origin
git worktree add --detach /opt/verity-site origin/feat/website-deploy

cd /opt/verity-site
cp infra/docker/.env.website.example infra/docker/.env.website
bash infra/scripts/deploy-site.sh
```

The script builds the image, starts the container, waits for it to be healthy, checks that the
address was baked into the pages, connects the edge nginx to the site's network (once) and
prints what the public address answers. It answers 200 only after the next section is done.

## Edge server block and certificate

The edge is not ours, so this part is done by hand. `infra/docker/edge-nginx-website.conf.example`
holds both blocks. In order:

1. Add the HTTP block, test and reload (`docker exec <edge> nginx -t && docker exec <edge> nginx -s reload`).
2. Issue a certificate for the hostname the way the edge already does it for `runwaydream.com`
   (HTTP challenge through the block from step 1).
3. Add the HTTPS block with the certificate paths, test and reload.

The HTTPS block resolves `verity-site` through Docker's DNS on every few seconds instead of once
at load, so redeploying the site never needs an nginx reload. Do the same for any other
upstream: a name resolved once at load is what turns a rebuilt container into a 502.

## Update

```bash
cd /opt/verity && git fetch origin
cd /opt/verity-site && git checkout --detach origin/feat/website-deploy
bash infra/scripts/deploy-site.sh
```

Going back is the same with the earlier commit. `docker compose --env-file infra/docker/.env.website
-f infra/docker/docker-compose.website.yml down` takes the site offline; the platform is not affected.

## Moving to the real hostname

1. DNS: one `A` record for the chosen name (`website`, `www` or the bare domain) pointing at the
   server's IP, added where `runwaydream.com`'s DNS is hosted. The platform's records are not touched.
2. Certificate for the new name, then a new HTTPS block for it in the edge (drop `X-Robots-Tag`,
   add `Strict-Transport-Security`), test and reload.
3. `SITE_URL` in `infra/docker/.env.website` to the new address, then `bash infra/scripts/deploy-site.sh`.
   The canonical links, sitemap and robots.txt carry the address, so the rebuild is required.
4. Remove the sslip.io block and its certificate once the new address works.

## Not set yet

The demo request endpoint, the "Was this page helpful?" endpoint and the privacy and terms links
are empty on purpose (`website/README.md`, "Before going live"). Fill them in the settings file
when they exist; an endpoint's origin must also be added to `connect-src` in `website/nginx.conf`.
