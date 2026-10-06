# syntax=docker/dockerfile:1.7
#
# Builds the public website (a Next.js static export) and serves it from nginx. Nothing
# runs on Node in production: `next build` writes plain files to out/ and nginx serves them.
#
# SITE_URL and APP_URL are baked into those files (canonical links, sitemap, robots.txt,
# the Start trial and Sign in targets), so changing either one means rebuilding the image.
# docker-compose.website.yml passes them in from infra/docker/.env.website.

# ---- build -----------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# devDependencies are required: tailwind, postcss and typescript run during the build.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# No default for SITE_URL on purpose. The build fails when it is empty instead of
# publishing a site whose canonical links point somewhere else.
ARG SITE_URL
ARG APP_URL
ARG NEXT_PUBLIC_DEMO_ENDPOINT
ARG NEXT_PUBLIC_FEEDBACK_ENDPOINT
ARG PRIVACY_URL
ARG TERMS_URL
ENV SITE_URL=$SITE_URL \
    APP_URL=$APP_URL \
    NEXT_PUBLIC_DEMO_ENDPOINT=$NEXT_PUBLIC_DEMO_ENDPOINT \
    NEXT_PUBLIC_FEEDBACK_ENDPOINT=$NEXT_PUBLIC_FEEDBACK_ENDPOINT \
    PRIVACY_URL=$PRIVACY_URL \
    TERMS_URL=$TERMS_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ---- runtime ---------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/out /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=4s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1
