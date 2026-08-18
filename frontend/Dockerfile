# syntax=docker/dockerfile:1.7
#
# Builds the SPA to static files and serves them from nginx.
#
# This nginx is OURS and owns all app routing: SPA fallback, the /api prefix, cache
# headers. The edge proxy in front of it (on a shared host, somebody else's) only
# needs to forward traffic here, so routing changes never require touching their
# config again.

# ---- build -----------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# devDependencies are REQUIRED here. vite, typescript and msw are all devDeps, and
# `npm run build` runs `tsc -b` first, which typechecks src/mocks/* — and that
# imports msw/browser. `npm ci --omit=dev` fails the build.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Set explicitly rather than relying on absence: Vite reads VITE_* from the process
# environment, not only from .env files. A stray VITE_USE_MOCKS=true on a build host
# bakes MSW into the bundle, and the app then never talks to the real API — which
# looks like a working deploy serving fabricated data. In a compliance product that
# is the worst possible failure mode, so it is pinned here.
ENV VITE_USE_MOCKS=false

# The mock service worker is a public/ asset, so it is copied into dist/
# unconditionally, whether or not mocks are enabled. It is inert unless startWorker()
# registers it, but a mock interceptor has no business on a production origin.
RUN npm run build && rm -f dist/mockServiceWorker.js

# ---- runtime ---------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=4s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1
