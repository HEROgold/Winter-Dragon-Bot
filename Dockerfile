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

# Copy project files - explicit paths since glob patterns don't work well
COPY wd-bot/ wd-bot/
COPY wd-config/ wd-config/
COPY wd-core/ wd-core/
COPY wd-db/ wd-db/
COPY wd-discord/ wd-discord/
COPY wd-errors/ wd-errors/
COPY wd-types/ wd-types/
COPY discord.py/ discord.py/
COPY src/ src/
COPY uv.lock pyproject.toml config.ini README.md LICENSE.md ./

# Build dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.15-rc-slim-trixie

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/wd-bot /app/wd-bot
COPY --from=builder /app/wd-config /app/wd-config
COPY --from=builder /app/wd-core /app/wd-core
COPY --from=builder /app/wd-db /app/wd-db
COPY --from=builder /app/wd-discord /app/wd-discord
COPY --from=builder /app/wd-errors /app/wd-errors
COPY --from=builder /app/wd-types /app/wd-types
COPY --from=builder /app/src /app/src
COPY --from=builder /app/config.ini /app/

WORKDIR /app

# Create logs directory
RUN mkdir -p /app/logs

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "winter_dragon.bot"]
