# syntax=docker/dockerfile:1.7
#
# Production image for the API and the Celery worker (same image, different CMD).
#
# Local development does NOT use this: `make run` runs uvicorn natively against the
# infra compose stack, because bind-mount file watching from Windows into a Linux
# container is slow enough to change how you work. This image is the shipping
# format, not the editing environment.

# ---- builder ---------------------------------------------------------------
# Same base as the runtime stage, with the uv binary copied in. Astral does not
# publish a combined uv+python tag for every release (0.12.3-python3.12-bookworm-slim
# does not exist), and this way the wheels are compiled against exactly the
# interpreter that will run them — asyncpg, cryptography and argon2-cffi are all
# native builds, so a mismatched base is a runtime import error, not a build error.
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies resolve in their own layer so a code-only change — the daily case —
# reuses the entire install. --frozen fails rather than silently re-resolving if
# uv.lock and pyproject.toml have drifted apart.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# `[tool.uv] package = true`, so this second sync installs the verity package itself
# into the venv. That is what lets `uvicorn verity.main:app` resolve with no PYTHONPATH.
COPY src ./src
COPY scripts ./scripts
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 1001 verity \
 && useradd --system --uid 1001 --gid verity --no-create-home verity

WORKDIR /app
COPY --from=builder --chown=verity:verity /app /app

# Evidence files land under .data/objects (storage.local_root, relative to this
# WORKDIR). The directory must exist in the image and be owned by the runtime
# user: Docker seeds a fresh named volume from the image path it is mounted over,
# so if this is absent the volume is created root-owned and uid 1001 cannot write
# to it — the upload then fails at runtime, not at build time.
RUN mkdir -p /app/.data/objects && chown -R verity:verity /app/.data

USER verity
EXPOSE 8000

# /healthz and /readyz are unprefixed (core/health.py) — they do not sit under
# /api/v1. /healthz is liveness only; /readyz returns 503 when Postgres or Redis is
# unreachable, which is the wrong signal for "should Docker restart this container".
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

# WORKDIR matters: core/config.py reads _ENV_FILES = ("../.env", ".env") relative to
# the process CWD. Nothing mounts an .env here — configuration arrives as real
# environment variables from compose — but the CWD must stay predictable regardless.
CMD ["uvicorn", "verity.main:app", "--host", "0.0.0.0", "--port", "8000"]
