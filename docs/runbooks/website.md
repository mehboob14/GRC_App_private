# Public website

The public site (`website/`, a Next.js static export) runs on the same server as the platform
but as its own compose project, `verity-site`: one nginx container serving files that were
built into its image. No database, no secrets, no Node at runtime. It shares no network with
the platform, so a bad site deploy cannot reach the app.

| | |
|---|---|
| Container | `verity-site` (nginx, port 80 inside, nothing published) |
| Compose | `infra/docker/docker-compose.website.yml`, settings in `infra/docker/.env.website` (per server, not committed) |
| Checkout | `~/verity-site` (the deploying user's home, which needs no sudo), a detached git worktree of the platform repository in `/opt/verity`, so the platform's own checkout stays on its branch |
| Address | `SITE_URL` in the settings file. Temporary: `https://website.37-60-228-227.sslip.io` |
| HTTPS | ends at the edge nginx (`keycloak-nginx`), which proxies to `verity-site` |

## First time

```bash
cd /opt/verity && git fetch origin
git worktree add --detach ~/verity-site origin/feat/website-deploy

cd ~/verity-site
cp infra/docker/.env.website.example infra/docker/.env.website
bash infra/scripts/deploy-site.sh
```

The script builds the image, starts the container, waits for it to be healthy, checks that the
address was baked into the pages, connects the edge nginx to the site's network (once) and
prints what the public address answers. Until the next section is done that is not a 200: the
edge hands every hostname it does not know to the platform, with the platform's certificate.

## Edge server block and certificate

The edge (`keycloak-nginx`, with `keycloak-certbot` beside it) belongs to the Keycloak stack under
`/root/keycloak-saml`. Its config is root-owned and mounted read-only, so this step is for whoever
has root:

```bash
sudo bash /home/<deploying user>/verity-site/infra/scripts/edge-add-website.sh
```

It issues the certificate through the edge's own certbot folders (the edge's port 80 block already
answers the HTTP challenge for any hostname), installs the blocks from
`infra/docker/edge-nginx-website.conf.template` as `sites-enabled/website`, tests them with
`nginx -t` and only then reloads. If nginx rejects the blocks it removes them again, so a bad run
leaves the edge as it was. The platform's own blocks are not edited. It stops before changing
anything if the edge cannot reach `verity-site`.

The HTTPS block resolves `verity-site` through Docker's DNS every few seconds instead of once at
load, so redeploying the site never needs an nginx reload. Do the same for any other upstream: a
name resolved once at load is what turns a rebuilt container into a 502.

Connecting the edge to the site's network lasts until the edge container is recreated; running
`deploy-site.sh` again connects it again.

## Demo requests

The `/demo/` page posts to the platform: `POST {APP_URL}/api/v1/public/demo-requests`. The platform
keeps the request, emails the sales inbox (`LEADS_NOTIFY_EMAIL`, with the visitor's address as
Reply-To) and sends the visitor a short acknowledgement. Two things must be true on the platform:

1. It runs a version that has the endpoint. Deploy the platform first, then the site.
2. `LEADS_ALLOWED_ORIGINS` in the platform's `.env.production` lists this site's origin exactly, as a
   JSON list, for example `LEADS_ALLOWED_ORIGINS=["https://website.37-60-228-227.sslip.io"]`.
   Without it the browser blocks the request and the visitor sees "We could not send your request".
   Change it together with `SITE_URL` when the site moves to its real hostname.

The site's image allows the endpoint's origin in its Content-Security-Policy by itself: it reads the
same address the pages were built with.

## Update

```bash
cd /opt/verity && git fetch origin
cd ~/verity-site && git checkout --detach origin/feat/website-deploy
bash infra/scripts/deploy-site.sh
```

Going back is the same with the earlier commit. `docker compose --env-file infra/docker/.env.website
-f infra/docker/docker-compose.website.yml down` takes the site offline; the platform is not affected.

## Moving to the real hostname

1. DNS: one `A` record for the chosen name (`website`, `www` or the bare domain) pointing at the
   server's IP, added where `runwaydream.com`'s DNS is hosted. The platform's records are not touched.
2. Whoever has root runs `edge-add-website.sh <hostname>`. It replaces the temporary hostname's
   blocks with the new one's (no `noindex` header, HSTS added). The old certificate keeps renewing
   harmlessly until `certbot delete --cert-name website.37-60-228-227.sslip.io` removes it.
3. `SITE_URL` in `infra/docker/.env.website` to the new address, then `bash infra/scripts/deploy-site.sh`.
   The canonical links, sitemap and robots.txt carry the address, so the rebuild is required.

## Not set yet

The "Was this page helpful?" endpoint and the privacy and terms links are empty on purpose
(`website/README.md`, "Before going live"). Fill them in the settings file when they exist; the image
build allows an endpoint's origin in the Content-Security-Policy.
