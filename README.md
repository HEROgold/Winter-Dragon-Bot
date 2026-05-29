# Winter Dragon Bot

## Frontend

This repository includes a React + Bun tsrx frontend with a user dashboard featuring Discord OAuth integration.

### Features

- **Counter Demo**: Local state management showcase on the home page
- **User Dashboard**: Authenticated view displaying user profile and data
- **Discord OAuth**: Sign in with Discord to access personalized data
- **Data Deletion**: GDPR-compliant soft delete with audit trail

### Running with Docker Compose

```bash
# Set Discord OAuth credentials
export DISCORD_CLIENT_ID="your-client-id"
export DISCORD_REDIRECT_URI="http://localhost:3000"

# Start all services
docker compose up --build
```

Services:
- **Frontend** (Bun + React): http://localhost:3000
- **API** (FastAPI): http://localhost:8001
- **Bot** (Discord.py): Connected to Discord
- **Redis**: Cache/queue backend
- **PostgreSQL**: Data persistence
- **PgAdmin**: Database UI at http://localhost:5050
- **Grafana**: Analytics UI at http://localhost:3002 for PostgreSQL data from `winter_dragon`
- **Redis Commander**: Cache UI at http://localhost:8081

### Local Frontend Development

```bash
cd frontend
bun install
bun run serve
```

The app will rebuild on file changes and serve at http://localhost:3000.

### API Endpoints

All endpoints require Bearer token authentication (except `/api/auth/discord/login` and `/api/auth/discord/callback`).

#### Authentication
- `GET /api/auth/discord/login` — Redirect to Discord OAuth
- `POST /api/auth/discord/callback` — Handle OAuth callback (called from frontend)

#### User Data
- `GET /api/user/{discord_id}` — Fetch user profile and summary
- `DELETE /api/user/{discord_id}/data` — Soft delete all user data
- `GET /api/user/{discord_id}/audit` — Fetch deletion audit trail

### OAuth Setup

1. Create a Discord application at https://discord.com/developers/applications
2. Copy the Client ID and set `DISCORD_CLIENT_ID`
3. Set OAuth2 Redirect URL to `http://localhost:3000` (local) or your production URL
4. Set `DISCORD_REDIRECT_URI` environment variable

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
Frontend (Bun + React + TSRX)
  ├── Home: Counter demo
  └── Dashboard: OAuth-protected view
        └── API Proxy to /api/*

API (FastAPI)
  ├── OAuth routes
  ├── User data queries
  └── Soft delete + audit logging

Bot (discord.py)
  ├── Discord commands/events
  └── Background workers
```

The frontend proxies `/api/*` requests to the FastAPI server running at `http://api:8001` (Docker) or `http://localhost:8001` (local).

### Next Steps

- Implement real Discord OAuth token exchange in `/src/winter_dragon/bot/api/routes.py`
- Connect API endpoints to actual database queries using SQLModel ORM
- Add authentication tokens (JWT or session-based)
- Set up audit logging for deletions
- Create comprehensive e2e tests for OAuth flow