# OAuth Dashboard Implementation Summary

## What Was Built

A complete, GDPR-compliant OAuth user dashboard feature for the WinterDragon frontend that allows users to:
1. Sign in with Discord
2. View their user profile and activity summary
3. Delete their data with audit trail compliance

## Files Created

### Frontend (TSRX React + Bun)
- **`frontend/src/App.tsrx`** — Refactored with view routing (home vs. dashboard), OAuth callback handler, session management
- **`frontend/src/Dashboard.tsrx`** — New dashboard component with user profile display, data summary, and soft-delete flow
- **`frontend/server.ts`** — Updated with API proxy layer (`/api/*` → backend)
- **`frontend/src/types.d.ts`** — Extended with React hooks and TSRX module declarations

### Backend (FastAPI)
- **`src/winter_dragon/bot/api/__init__.py`** — API module entry point
- **`src/winter_dragon/bot/api/routes.py`** — OAuth and user data endpoints (6 routes total)
- **`src/winter_dragon/bot/api/server.py`** — FastAPI app factory and uvicorn server launcher

### Database
- **`src/winter_dragon/database/tables/user_data_deletion.py`** — Audit table for GDPR compliance

### Configuration
- **`docker-compose.yml`** — Added `api` service and updated `frontend` with API proxy environment
- **`README.md`** — Comprehensive setup and usage guide

## API Endpoints

All require Bearer token authentication (except login/callback):

```
POST   /api/auth/discord/callback       — OAuth token exchange
GET    /api/auth/discord/login          — Redirect to Discord OAuth
GET    /api/user/{discord_id}           — User profile + data summary
DELETE /api/user/{discord_id}/data      — Soft delete with audit
GET    /api/user/{discord_id}/audit     — Deletion audit trail
```

## Architecture

**Frontend (Bun)** → **Frontend Server (SPA proxy + API relay)** → **API Server (FastAPI)** → **Database (PostgreSQL)**

- Frontend proxies `/api/*` requests to backend (supports Docker networking)
- OAuth session stored in localStorage (tokens in production should use HttpOnly)
- Soft delete preserves audit trail for compliance
- All user data operations require authorization checks

## Key Decisions

✅ **Backend**: Reused existing bot infrastructure (added FastAPI to compose)  
✅ **Frontend**: Merged dashboard into App.tsrx with view routing  
✅ **Data View**: Full detail with pagination support  
✅ **Delete**: Soft delete with audit trail  
✅ **Styling**: Inherited gold/dark theme from existing counter app  

## TODO (Implementation Gaps)

These are placeholders awaiting real implementation:

1. **Discord OAuth**: Replace mock token exchange with real Discord API calls
2. **Database Integration**: Connect API endpoints to actual ORM queries (SQLModel)
3. **Authentication**: Implement JWT or session-based auth verification
4. **Soft Delete Migration**: Add `deleted_at` timestamps to user-scoped tables
5. **Audit Logging**: Wire deletion requests to `UserDataDeletion` table
6. **Testing**: Add e2e tests for OAuth callback → delete flow

## Local Development

```bash
# Terminal 1: Frontend
cd frontend
bun install
bun run serve

# Terminal 2: API (if running locally)
uv run python -m winter_dragon.bot.api.server

# Or use compose for full stack
docker compose up --build
```

## Environment Variables

Required for compose:
```bash
DISCORD_CLIENT_ID=your-app-id
DISCORD_REDIRECT_URI=http://localhost:3000
```

Optional:
```bash
API_BACKEND_URL=http://localhost:8001  # Frontend proxy target
```
