# syntax=docker/dockerfile:1.7-labs
FROM python:3.15-rc-slim-trixie AS builder

# Don't write .pyc files during the build. The uv cache lives on a cache
# mount, so copy out of it instead of hardlinking, and use the image's Python.
ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Copy uv binary from official image
COPY --from=docker.io/astral/uv:0.11.7 /uv /uvx /bin/

WORKDIR /app

# Third-party dependencies first, from the lock and the workspace manifests
# only, so source edits reuse this layer. Every runtime dependency ships a
# cp315 wheel, so no compiler is installed; --no-build fails fast if a future
# dependency would need one.
COPY uv.lock pyproject.toml ./
COPY --parents wd-*/pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --no-build

# Then the workspace packages themselves
COPY README.md LICENSE.md ./
COPY --parents wd-*/ ./
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage
FROM python:3.15-rc-slim-trixie AS runtime

# Don't write .pyc files at runtime
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Create a non-root user (fixed uid/gid 10001, so USER and host bind mounts
# resolve it numerically) that owns the app tree (including the logs directory,
# so it stays writable when ./logs is bind-mounted by compose). Ownership is
# set while copying: a later `chown -R` would duplicate the whole venv layer.
RUN groupadd -r -g 10001 appuser \
    && useradd -r -l -u 10001 -g appuser appuser \
    && mkdir -p /app/logs \
    && chown 10001:10001 /app /app/logs

# Copy source packages for production (resolve .pth file warnings)
COPY --from=builder --chown=10001:10001 --parents /app/./wd-*/src /app/

# Copy other build artifacts. The ini files are operator config (token, database
# password), so they're never baked in: compose bind-mounts them into /app.
COPY --from=builder --chown=10001:10001 /app/src /app/src
COPY --from=builder --chown=10001:10001 /app/.venv /app/.venv

# No need to copy uv to runtime if using venv directly
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Documents the port used by the `web` service (the dashboard); bot/workers don't listen.
EXPOSE 8001

# Port-independent liveness check that works for all three services
# (bot, workers, web) built from this image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import winter_dragon"]

USER 10001:10001

CMD ["python", "-m", "winter_dragon"]
