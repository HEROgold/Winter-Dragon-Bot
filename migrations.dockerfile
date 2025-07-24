FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Install UV package manager
RUN pip install uv

# Install project dependencies
RUN uv sync

# Install the workspace packages in the correct order
RUN uv pip install -e ./database -e ./bot -e ./backend

# Install Alembic explicitly
RUN uv pip install alembic asyncpg

# Create entrypoint script
COPY migrations.entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD []
