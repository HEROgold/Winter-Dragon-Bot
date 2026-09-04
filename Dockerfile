# syntax=docker/dockerfile:1.7-labs
FROM python:3.15-rc-slim-trixie AS builder

# Don't write .pyc files during the build
ENV PYTHONDONTWRITEBYTECODE=1

# Copy uv binary from official image
COPY --from=docker.io/astral/uv:0.11.7 /uv /uvx /bin/

WORKDIR /app

# Install only build dependencies.
# Versions are pinned for reproducible builds; refresh these when the
# python:3.15-rc-slim-trixie base image updates (Debian drops old versions
# from mirrors). Resolve current versions with:
#   docker run --rm python:3.15-rc-slim-trixie sh -c \
#     "apt-get update && apt-cache policy <pkg>"
RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.47.3-0+deb13u1 \
    build-essential=12.12 \
    python3-dev=3.13.5-1 \
    libssl-dev=3.5.7-1~deb13u2 \
    libffi-dev=3.4.8-2 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY uv.lock pyproject.toml config.ini README.md LICENSE.md ./
COPY --parents wd-*/ ./
COPY src/ src/

# Build dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.15-rc-slim-trixie AS runtime

# Don't write .pyc files at runtime
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy source packages for production (resolve .pth file warnings)
COPY --from=builder --parents /app/./wd-*/src /app/

# Copy other build artifacts
COPY --from=builder /app/config.ini /app/
COPY --from=builder /app/src /app/src
COPY --from=builder /app/.venv /app/.venv

# Create a non-root user and give it ownership of the app tree (including the
# logs directory, so it stays writable when ./logs is bind-mounted by compose).
RUN groupadd -r appuser && useradd -r -l -g appuser appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app

# No need to copy uv to runtime if using venv directly
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Documents the port used by the `api` service; bot/workers don't listen.
EXPOSE 8001

# Port-independent liveness check that works for all three services
# (bot, workers, api) built from this image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import winter_dragon" || exit 1

USER appuser

CMD ["python", "-m", "winter_dragon"]
