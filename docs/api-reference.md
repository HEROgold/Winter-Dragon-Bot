# API Reference

For interactive API documentation, visit http://localhost:8001/docs (Swagger UI) or http://localhost:8001/redoc (ReDoc) when the server is running.

## Authentication

All endpoints require Bearer token authentication unless noted otherwise.

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Token Acquisition

See [OAuth Endpoints](#oauth-endpoints) section below.

## Request/Response Format

### Success Response (2xx)

```json
{
  "data": {},
  "status": "success"
}
```

### Error Response

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

## OAuth Endpoints

### Login with Discord

**Endpoint**: `GET /api/auth/discord/login`

Redirects to Discord OAuth authorization page.

**Parameters**: None

**Response**: Redirect to Discord OAuth endpoint

**Example**:
```bash
curl -i https://localhost:8001/api/auth/discord/login
```

---

### OAuth Callback

**Endpoint**: `POST /api/auth/discord/callback`

Exchanges Discord authorization code for access token.

**Request Body**:
```json
{
  "code": "authorization_code_from_discord"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors**:
- `400 Bad Request` - Invalid authorization code
- `401 Unauthorized` - Failed to exchange code

**Example**:
```bash
curl -X POST http://localhost:8001/api/auth/discord/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "code_from_discord"}'
```

---

## User Endpoints

### Get User Profile

**Endpoint**: `GET /api/user/{discord_id}`

Retrieves authenticated user's profile information.

**Path Parameters**:
- `discord_id` (integer) - User's Discord ID

**Headers**:
- `Authorization: Bearer <token>` (required)

**Response** (200 OK):
```json
{
  "id": "123456789",
  "username": "john_doe",
  "discriminator": "0001",
  "avatar_url": "https://cdn.discordapp.com/avatars/...",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors**:
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Cannot access other user's data
- `404 Not Found` - User not found

**Example**:
```bash
curl -H "Authorization: Bearer token" \
  http://localhost:8001/api/user/123456789
```

---

### Request Data Deletion

**Endpoint**: `DELETE /api/user/{discord_id}/data`

Initiates GDPR-compliant data deletion for the authenticated user.

**Path Parameters**:
- `discord_id` (integer) - User's Discord ID

**Headers**:
- `Authorization: Bearer <token>` (required)

**Request Body** (optional):
```json
{
  "reason": "User requested deletion"
}
```

**Response** (202 Accepted):
```json
{
  "status": "deletion_requested",
  "deletion_id": "550e8400-e29b-41d4-a716-446655440000",
  "requested_at": "2024-01-01T00:00:00Z"
}
```

**Errors**:
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Cannot delete other user's data
- `404 Not Found` - User not found
- `409 Conflict` - Deletion already in progress

**Example**:
```bash
curl -X DELETE -H "Authorization: Bearer token" \
  http://localhost:8001/api/user/123456789/data \
  -H "Content-Type: application/json" \
  -d '{"reason": "I want to delete my data"}'
```

---

### Get Deletion Audit Trail

**Endpoint**: `GET /api/user/{discord_id}/audit`

Retrieves deletion request audit trail for the authenticated user.

**Path Parameters**:
- `discord_id` (integer) - User's Discord ID

**Query Parameters** (optional):
- `limit` (integer, default: 50) - Maximum results to return
- `offset` (integer, default: 0) - Results offset for pagination

**Headers**:
- `Authorization: Bearer <token>` (required)

**Response** (200 OK):
```json
{
  "deletions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "requested_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:05:00Z",
      "status": "completed",
      "reason": "User requested deletion"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "requested_at": "2024-01-02T10:30:00Z",
      "completed_at": null,
      "status": "pending",
      "reason": null
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Errors**:
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Cannot access other user's data
- `404 Not Found` - User not found

**Example**:
```bash
curl -H "Authorization: Bearer token" \
  "http://localhost:8001/api/user/123456789/audit?limit=10&offset=0"
```

---

## Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted for processing |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Request conflicts with current state |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal server error |

## Rate Limiting

Rate limits are applied per user token:

**Headers in Response**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

- **Limit**: 100 requests per hour
- **Reset**: Unix timestamp when limit resets

When rate limited (HTTP 429):
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

## Pagination

### Query Parameters

- `limit` (integer, max: 100, default: 50) - Results per page
- `offset` (integer, default: 0) - Number of results to skip

### Response Format

```json
{
  "data": [...],
  "total": 150,
  "limit": 50,
  "offset": 0,
  "next": "/api/resource?limit=50&offset=50",
  "prev": null
}
```

## Common Error Responses

### Invalid Token

```json
{
  "detail": "Invalid authentication credentials",
  "status_code": 401
}
```

### Insufficient Permissions

```json
{
  "detail": "Insufficient permissions to access resource",
  "status_code": 403
}
```

### Resource Not Found

```json
{
  "detail": "User not found",
  "status_code": 404
}
```

### Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "reason"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "status_code": 422
}
```

## SDKs and Examples

### Python

```python
import httpx
from typing import Optional

class WinterDragonClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.token: Optional[str] = None
    
    async def login_callback(self, code: str) -> str:
        """Exchange Discord code for token."""
        response = await self.client.post(
            f"{self.base_url}/api/auth/discord/callback",
            json={"code": code}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return self.token
    
    async def get_user(self, user_id: int):
        """Get user profile."""
        response = await self.client.get(
            f"{self.base_url}/api/user/{user_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self.client.aclose()
```

### JavaScript/TypeScript

```typescript
class WinterDragonClient {
  constructor(private baseUrl: string = "http://localhost:8001") {}
  
  private token?: string;
  
  async loginCallback(code: string): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/api/auth/discord/callback`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code })
      }
    );
    
    if (!response.ok) throw new Error("Login failed");
    const data = await response.json();
    this.token = data.access_token;
    return this.token;
  }
  
  async getUser(userId: number) {
    const response = await fetch(
      `${this.baseUrl}/api/user/${userId}`,
      {
        headers: { "Authorization": `Bearer ${this.token}` }
      }
    );
    
    if (!response.ok) throw new Error("Failed to fetch user");
    return response.json();
  }
}
```

## Related Documentation

- [API Usage Guide](guide/api-usage.md) - Usage examples and tutorials
- [Architecture](dev/architecture.md) - System design overview
- [Getting Started](guide/getting-started.md) - Setup instructions
