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
COPY --parents wd-*/ ./
COPY discord.py/ discord.py/
COPY src/ src/
COPY uv.lock pyproject.toml config.ini README.md LICENSE.md ./

# Build dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.15-rc-slim-trixie

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/wd-*/ /app/wd-*/
COPY --from=builder /app/config.ini /app/

WORKDIR /app

# Create logs directory
RUN mkdir -p /app/logs

# No need to copy uv to runtime if using venv directly
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "winter_dragon.bot"]
