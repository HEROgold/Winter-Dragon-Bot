# Architecture

## System Overview

Winter Dragon is a multi-service Discord bot platform with a modular architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│         React + Bun + TSRX (SPA)                           │
│              http://localhost:3000                          │
└─────────────────────────────────────────────────────────────┘
                          │
                   (OAuth + REST API)
                          │
┌─────────────────────────────────────────────────────────────┐
│                     API Layer                               │
│    FastAPI Application                                      │
│    - OAuth2 Endpoints (/api/auth/*)                        │
│    - User Routes (/api/user/*)                             │
│    - Admin Routes (/api/admin/*)                           │
│         http://localhost:8001                              │
└─────────────────────────────────────────────────────────────┘
            │                    │                    │
            ├──────┬────────────┬┴──────┐             │
            │      │            │       │             │
┌───────────▼─┐ ┌──▼──┐  ┌──────▼──┐  │   ┌─────────▼───┐
│ PostgreSQL  │ │Redis│  │ Bot Core│  │   │   Workers   │
│   (DB)      │ │(Key)│  │ discord │  │   │   Service   │
│             │ │Value│  │  .py    │  │   │             │
└─────────────┘ └─────┘  └─────────┘  │   └─────────────┘
                                       │
                    ┌──────────────────┘
                    │
        ┌───────────▼───────────┐
        │ Discord Gateway       │
        │ (Events & Commands)   │
        └───────────────────────┘
```

## Component Architecture

### Frontend (React + Bun)

- **SPA** (Single Page Application) using React
- **TSRX** for state management and routing
- **OAuth 2.0** integration with Discord
- **Protected Routes** for authenticated views
- **Real-time** updates via API polling

### API Server (FastAPI)

- **REST API** with OpenAPI documentation
- **SQLModel ORM** for database operations
- **Async Support** for concurrent request handling
- **Bearer Token** authentication
- **CORS** enabled for frontend integration

### Bot Service (discord.py)

- **Event Handlers** for Discord events
- **Command Framework** for slash commands
- **Background Tasks** via Redis queue
- **Database Integration** for persistent data

### Worker Service

- **Async Tasks** from Redis queue
- **Background Processing** (emails, heavy computation)
- **Scheduled Jobs** (cron-like tasks)

### Data Layer

#### PostgreSQL Database

- **User Profiles** - Discord user data
- **User Data Deletion** - GDPR audit trail
- **Game Records** - Player statistics
- **Authorization** - OAuth tokens and sessions

#### Redis Cache

- **Session Storage** - User session data
- **Job Queue** - Background task queue
- **Real-time Data** - Transient caching

## Data Flow

### User Authentication

```
1. User clicks "Sign in with Discord"
   │
2. Frontend → API (/api/auth/discord/login)
   │
3. API → Discord OAuth Endpoint
   │
4. User authorizes on Discord
   │
5. Discord → API Callback
   │
6. API exchanges code for token
   │
7. API → Frontend (token)
   │
8. Frontend stores token, redirects to /dashboard
```

### Data Access

```
1. Frontend request → API endpoint (with token)
   │
2. API validates token via Redis
   │
3. API queries PostgreSQL
   │
4. PostgreSQL → API (data)
   │
5. API → Frontend (JSON response)
```

### Background Processing

```
1. API receives request requiring async work
   │
2. API enqueues job to Redis queue
   │
3. Worker picks up job from queue
   │
4. Worker processes and updates database
   │
5. API notifies frontend (optional)
```

## Service Communication

### Inter-Service

- **API ↔ PostgreSQL**: SQLModel ORM, connection pooling
- **API ↔ Redis**: Redis client (caching, sessions)
- **Bot ↔ PostgreSQL**: SQLModel ORM
- **Bot ↔ Redis**: Job queue, state sharing
- **Worker ↔ Redis**: Job queue processing
- **Worker ↔ PostgreSQL**: Data persistence

### External

- **API ↔ Discord OAuth**: HTTP requests
- **Bot ↔ Discord**: WebSocket (gateway)
- **Frontend ↔ API**: REST API over HTTP

## Deployment Architecture

### Docker Compose

Each service runs in its own container:
- `redis` - Cache layer
- `postgres` - Database
- `api` - FastAPI server
- `bot` - Discord bot
- `workers` - Background workers
- `pgadmin` - Database admin UI
- `grafana` - Analytics dashboard

### Environment Configuration

Services communicate via Docker DNS:
- `postgres:5432` - Database host
- `redis:6379` - Cache host
- Services share the same network

## Security

### Authentication

- **OAuth 2.0** with Discord for user authentication
- **Bearer Tokens** for API access (JWT recommended)
- **Session Storage** in Redis with TTL

### Data Protection

- **Password Hashing** for sensitive data
- **HTTPS** enforced in production
- **CORS** restricted to whitelisted origins
- **SQL Injection** prevention via ORM

### Audit Trail

- **GDPR Compliance** with deletion audit logs
- **User Data Deletion** soft-delete approach
- **Timestamp Tracking** for all operations

## Scaling Considerations

### Horizontal Scaling

- **Multiple API instances** behind load balancer
- **Multiple Workers** consuming from Redis queue
- **Read replicas** for PostgreSQL
- **Redis Sentinel** for HA

### Caching Strategy

- **User profiles** cached in Redis
- **Session data** stored in Redis with TTL
- **Database query results** cached where applicable

### Database Optimization

- **Indexes** on frequently queried columns
- **Connection pooling** for concurrent access
- **Query optimization** using SQLModel
