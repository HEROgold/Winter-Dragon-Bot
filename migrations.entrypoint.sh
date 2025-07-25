#!/bin/bash
set -e
echo "Starting Alembic migrations..."
echo "Waiting for database to be ready..."
until pg_isready -h postgres -p 5432 -U postgres; do
  echo "Waiting for postgres..."
  sleep 2
done
echo "Database is ready!"

# Check if this is a migration generation request
if [ "$1" = "generate" ]; then
  shift
  echo "Generating new migration..."
  if [ -z "$1" ]; then
    echo "Error: Migration message is required when using generate command"
    echo "Usage: docker run <image> generate \"migration message\""
    exit 1
  fi
  uv run alembic revision --autogenerate -m "$1"
  echo "Migration generated successfully!"
  exit 0
fi

# Auto-generate migrations if no versions exist
if [ ! "$(ls -A /app/migrations/versions 2>/dev/null)" ]; then
  echo "No existing migrations found. Generating initial migration..."
  uv run alembic revision --autogenerate -m "Initial migration"
  echo "Initial migration generated!"
fi

# Check for pending schema changes and generate migration if needed
echo "Checking for schema changes..."
if uv run alembic check 2>/dev/null; then
  echo "No schema changes detected."
else
  echo "Schema changes detected. Generating new migration..."
  timestamp=$(date +"%Y%m%d_%H%M%S")
  uv run alembic revision --autogenerate -m "Auto-generated migration $timestamp"
  echo "New migration generated!"
fi

# Apply migrations
echo "Applying migrations..."
uv run alembic upgrade head
echo "Migrations applied successfully!"

# If no additional command specified, show current status
if [ $# -eq 0 ]; then
  echo "Current migration status:"
  uv run alembic current
  uv run alembic history --verbose
else
  # Use uv run to ensure proper environment for custom commands
  exec uv run "$@"
fi
