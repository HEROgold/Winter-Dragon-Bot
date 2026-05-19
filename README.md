# Winter Dragon Bot

## Dashboard

This repository now includes a FastAPI + HTMX dashboard with Discord OAuth for user self-service.

### Features

- **Discord OAuth**: Sign in with Discord to access personalized data
- **HTMX Dashboard**: Server-rendered templates with live partial updates
- **User Data View**: Authenticated data summary and audit history
- **Data Deletion Requests**: GDPR-style deletion request logging with audit trail

### Running with Docker Compose

```bash
# Set Discord OAuth credentials
export DISCORD_CLIENT_ID="your-client-id"
export DISCORD_CLIENT_SECRET="your-client-secret"
export DISCORD_REDIRECT_URI="http://localhost:8001/api/auth/discord/callback"

# Start all services
docker compose up --build
```

Services:
- **Dashboard + API** (FastAPI + HTMX): http://localhost:8001
- **Bot** (Discord.py): Connected to Discord
- **Redis**: Cache/queue backend
- **PostgreSQL**: Data persistence
- **PgAdmin**: Database UI at http://localhost:5050
- **Redis Commander**: Cache UI at http://localhost:8081

### Local Dashboard Development

```bash
uv run python -m winter_dragon.bot.api.server
```

Open `http://localhost:8001` and sign in with Discord.

### API Endpoints

HTML dashboard routes:
- `GET /` — Redirects to dashboard login
- `GET /api/login` — Login page
- `GET /api/dashboard` — Authenticated HTMX dashboard

JSON endpoints require Bearer token authentication (except login/callback).

#### Authentication
- `GET /api/auth/discord/login` — Redirect to Discord OAuth
- `GET /api/auth/discord/callback` — Browser OAuth callback handler
- `POST /api/auth/discord/callback` — API callback handler
- `POST /api/auth/logout` — Clear session cookie

#### HTMX Endpoints
- `GET /api/htmx/user-data` — Render user data partial
- `GET /api/htmx/user-audit` — Render deletion audit partial
- `POST /api/htmx/delete-data` — Submit deletion request

#### User Data
- `GET /api/user/{discord_id}` — Fetch user profile and summary
- `DELETE /api/user/{discord_id}/data` — Soft delete all user data
- `GET /api/user/{discord_id}/audit` — Fetch deletion audit trail

### OAuth Setup

1. Create a Discord application at https://discord.com/developers/applications
2. Copy the Client ID and set `DISCORD_CLIENT_ID`
3. Copy the Client Secret and set `DISCORD_CLIENT_SECRET`
4. Set OAuth2 Redirect URL to `http://localhost:8001/api/auth/discord/callback` (local)
5. Set `DISCORD_REDIRECT_URI` environment variable to the exact same callback URL

### Clerk Components (Safe UI Auth Components)

To render Clerk sign-in/user components in the dashboard templates, set:

```bash
CLERK_PUBLISHABLE_KEY=pk_test_...
```

When this key is present, login/dashboard pages mount Clerk components for authorization UI.

### Database Schema

**New Tables:**
- `user_data_deletion` — Audit log for GDPR data deletion requests

**Related User Tables:**
- `user` — Core user data
- `incremental.player` — Game statistics
- `game` — Game records
- And other user-scoped tables in `/src/winter_dragon/database/tables/`

### Architecture

```
API (FastAPI)
  ├── Jinja2 templates (login/dashboard)
  ├── HTMX partial routes
  ├── Discord OAuth routes
  └── User data + deletion audit routes

Bot (discord.py)
  ├── Discord commands/events
  └── Background workers
```

### Next Steps

- Add secure production cookie settings (`secure=True`, HTTPS only)
- Expand user data exports to more user-scoped tables
- Add e2e tests for OAuth flow and HTMX dashboard actions
