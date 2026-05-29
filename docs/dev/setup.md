# Development Setup

## Prerequisites

- Python 3.15+
- Bun (for frontend)
- Docker and Docker Compose
- Git
- A code editor (VS Code recommended)

## Local Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/HEROgold/Winter-Dragon-Bot.git
cd Winter-Dragon-Bot
git checkout v2
```

### 2. Install Python Dependencies

Using UV (fast Python package manager):

```bash
# Install all workspace dependencies
uv sync

# Or install specific workspaces
uv sync --group wd-bot
```

### 3. Setup Environment Variables

Create `.env` file in project root:

```env
# Python
PYTHON_LAZY_IMPORTS=all

# Database
DB_PASSWORD=dev-password-change-in-prod

# Discord OAuth
DISCORD_CLIENT_ID=your-client-id
DISCORD_REDIRECT_URI=http://localhost:3000

# Admin Interfaces
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=dev-password

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=dev-password
```

### 4. Start Services

```bash
# Build and start all services
docker compose up --build

# Or in background
docker compose up -d --build
```

### 5. Frontend Development

In a new terminal:

```bash
cd frontend
bun install
bun run serve
```

Frontend will auto-reload on file changes.

## Project Structure

```
WinterDragonV2/
├── docs/                          # MkDocs documentation
│   ├── guide/                     # User guides
│   ├── dev/                       # Developer guides
│   └── index.md                   # Home page
├── src/winter_dragon/
│   ├── bot/
│   │   ├── api/                   # FastAPI server
│   │   ├── cogs/                  # Discord bot cogs
│   │   └── __main__.py           # Bot entry point
│   ├── database/
│   │   ├── tables/               # SQLModel ORM tables
│   │   └── manager.py            # Database manager
│   ├── workers/                  # Background tasks
│   └── __main__.py               # Main entry point
├── frontend/                      # React + Bun frontend
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── main.tsx
│   └── vite.config.ts
├── wd-bot/                       # Bot workspace package
├── wd-db/                        # Database workspace package
├── wd-discord/                   # Discord extensions
├── wd-core/                      # Core utilities
├── wd-errors/                    # Error handling
├── wd-types/                     # Type definitions
└── pyproject.toml               # Main project config
```

## Development Workflow

### Adding Database Tables

1. Create table definition in `src/winter_dragon/database/tables/`
2. Use SQLModel for type hints and ORM
3. Run migration or recreate containers

Example:

```python
# src/winter_dragon/database/tables/my_table.py
from sqlmodel import SQLModel, Field
from typing import Optional

class MyTable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    data: str
```

### Adding API Endpoints

1. Create route in `src/winter_dragon/bot/api/routes.py`
2. Use FastAPI decorators
3. Add SQLModel schemas for request/response

Example:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/my-resource", tags=["my-resource"])

@router.get("/{id}")
async def get_resource(id: int):
    return {"id": id}
```

### Adding Discord Bot Commands

1. Create cog in `src/winter_dragon/bot/cogs/`
2. Extend `commands.Cog`
3. Use decorators for commands/listeners

Example:

```python
# src/winter_dragon/bot/cogs/my_cog.py
from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def mycommand(self, ctx):
        await ctx.send("Hello!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

### Adding Background Jobs

1. Create task in `src/winter_dragon/workers/`
2. Enqueue from API via Redis
3. Worker processes asynchronously

## Testing

### Run Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_api.py

# With coverage
uv run pytest --cov=src
```

### Test Structure

```
tests/
├── test_api.py              # API endpoint tests
├── test_database.py         # Database tests
├── test_bot.py             # Bot tests
└── conftest.py             # Pytest fixtures
```

## Code Quality

### Type Checking

```bash
uv run pyright
```

### Linting

```bash
uv run ruff check .
```

### Formatting

```bash
uv run ruff format .
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Debugging

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api

# Last 100 lines
docker compose logs -f --tail=100
```

### Access Database

Using PgAdmin:
1. Navigate to http://localhost:5050
2. Login with credentials from `.env`
3. Query database directly

### Debug API

FastAPI provides Swagger UI at http://localhost:8001/docs for interactive testing.

### Debug Bot

Enable debug logging in bot startup:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Common Tasks

### Rebuild Containers

```bash
docker compose up --build --force-recreate
```

### Reset Database

```bash
docker compose down -v  # Remove volumes
docker compose up       # Recreate volumes
```

### View Database Migrations

Check `IMPLEMENTATION.md` for database schema overview.

## Troubleshooting

### Import Errors

Ensure workspace dependencies are installed:

```bash
uv sync --all-groups
```

### Database Connection Fails

Verify PostgreSQL is running:

```bash
docker compose ps postgres
```

### API Not Accessible

Check if service started:

```bash
docker compose logs api
```

### Bot Won't Connect

Verify Discord token and permissions are set correctly in config.

## Next Steps

- Review [Architecture](architecture.md) for system design
- Check [Database Schema](database.md) for data models
- Read [API Usage](../guide/api-usage.md) for integration examples
