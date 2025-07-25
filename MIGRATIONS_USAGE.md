# Database Migrations Container Usage

This document describes how to use the migrations Docker container for automated database schema management using Alembic.

## Overview

The migrations container automatically handles database schema changes by:

- Detecting when no migrations exist and generating an initial migration
- Checking for schema changes and creating new migrations automatically
- Applying all pending migrations to the database
- Providing manual migration generation capabilities

## Building the Container

```bash
docker build -f migrations.dockerfile -t winter-dragon-migrations .
```

## Usage Scenarios

### 1. Automatic Migration Workflow (Default)

Run the container without any arguments to automatically handle migrations:

```bash
docker run --rm winter-dragon-migrations
```

**What this does:**

1. Waits for the PostgreSQL database to be ready
2. Generates an initial migration if none exist
3. Checks for schema changes in your SQLModel definitions
4. Creates new migrations if changes are detected
5. Applies all pending migrations to the database
6. Shows the current migration status

### 2. Manual Migration Generation

Generate a migration with a custom message:

```bash
docker run --rm winter-dragon-migrations generate "Add user authentication tables"
```

**Requirements:**

- A migration message must be provided
- The container will exit after generating the migration

### 3. Run Custom Alembic Commands

Execute any Alembic command through the container:

```bash
docker run --rm winter-dragon-migrations alembic history --verbose
docker run --rm winter-dragon-migrations alembic current
docker run --rm winter-dragon-migrations alembic show
...
```

## Docker Compose Integration

### Running with Docker Compose

```bash
# Run automatic migrations
docker-compose up migrations

# Generate a specific migration
docker-compose run --rm migrations generate "Add new feature tables"

# Run custom Alembic commands
docker-compose run --rm migrations alembic history
```

## Environment Variables

The container uses the following environment variables:

- `PYTHONPATH=/app` - Ensures proper Python module resolution
- `PATH="/app/.venv/bin:$PATH"` - Uses the UV virtual environment

Database connection is configured in `alembic.ini`:
