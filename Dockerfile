# syntax=docker/dockerfile:1.7-labs
FROM python:3.15-rc-slim-trixie AS builder

# Copy uv binary from official image
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install only build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    python3-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY uv.lock pyproject.toml config.ini README.md LICENSE.md ./
COPY --parents wd-*/ ./
COPY src/ src/

# Build dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.15-rc-slim-trixie

WORKDIR /app

# Copy source packages for production (resolve .pth file warnings)
COPY --from=builder /app/wd-bot/src /app/wd-bot/src
COPY --from=builder /app/wd-config/src /app/wd-config/src
COPY --from=builder /app/wd-core/src /app/wd-core/src
COPY --from=builder /app/wd-db/src /app/wd-db/src
COPY --from=builder /app/wd-discord/src /app/wd-discord/src
COPY --from=builder /app/wd-errors/src /app/wd-errors/src
COPY --from=builder /app/wd-types/src /app/wd-types/src
COPY --from=builder /app/wd-cogs/src /app/wd-cogs/src

# Copy other build artifacts
COPY --from=builder /app/config.ini /app/
COPY --from=builder /app/src /app/src
COPY --from=builder /app/.venv /app/.venv

# Create logs directory
RUN mkdir -p /app/logs

# No need to copy uv to runtime if using venv directly
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "winter_dragon"]
