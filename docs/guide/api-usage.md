# API Usage Guide

## Overview

The Winter Dragon API is a **FastAPI** application providing REST endpoints for user data management, authentication, and server operations.

## Base URL

- **Development**: `http://localhost:8001`
- **Production**: Configure via `DISCORD_REDIRECT_URI`

## Authentication

All endpoints (except OAuth callbacks) require Bearer token authentication:

```http
Authorization: Bearer <your-token>
```

## Endpoints

### OAuth & Authentication

#### Discord OAuth Login

```http
GET /api/auth/discord/login
```

Redirects to Discord OAuth authorization page.

#### OAuth Callback Handler

```http
POST /api/auth/discord/callback
Content-Type: application/json

{
  "code": "discord-authorization-code"
}
```

Exchanges authorization code for user token.

**Response:**
```json
{
  "access_token": "user-jwt-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### User Data

#### Get User Profile

```http
GET /api/user/{discord_id}
Authorization: Bearer <token>
```

Returns user profile and summary.

**Response:**
```json
{
  "id": "123456789",
  "username": "username",
  "discriminator": "0001",
  "avatar_url": "https://cdn.discordapp.com/avatars/...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Request Data Deletion

```http
DELETE /api/user/{discord_id}/data
Authorization: Bearer <token>
```

Initiates GDPR-compliant data deletion. Creates audit trail entry.

**Response:**
```json
{
  "status": "deletion_requested",
  "deletion_id": "uuid",
  "requested_at": "2024-01-01T00:00:00Z"
}
```

#### Get Deletion Audit Trail

```http
GET /api/user/{discord_id}/audit
Authorization: Bearer <token>
```

Returns history of data deletion requests.

**Response:**
```json
{
  "deletions": [
    {
      "id": "uuid",
      "requested_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:05:00Z",
      "status": "completed"
    }
  ]
}
```

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Server Error |

## Rate Limiting

API calls are rate-limited per user token. Check response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Examples

### Python

```python
import httpx

async with httpx.AsyncClient() as client:
    # Login
    response = await client.post(
        "http://localhost:8001/api/auth/discord/callback",
        json={"code": "discord-code"}
    )
    token = response.json()["access_token"]
    
    # Get user profile
    response = await client.get(
        "http://localhost:8001/api/user/123456789",
        headers={"Authorization": f"Bearer {token}"}
    )
    user = response.json()
```

### JavaScript/TypeScript

```typescript
const token = await getToken();

const response = await fetch(
  "http://localhost:8001/api/user/123456789",
  {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  }
);

const user = await response.json();
```

## Next Steps

- Review [Architecture](../dev/architecture.md) for system design
- Check [Database Schema](../dev/database.md) for data models
- Explore interactive API docs at `/docs` (Swagger UI)
