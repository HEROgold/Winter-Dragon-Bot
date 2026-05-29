# Getting Started

## Installation

### Prerequisites

- Docker and Docker Compose
- Discord Developer Application credentials
- Git

### Setup Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/HEROgold/Winter-Dragon-Bot.git
cd Winter-Dragon-Bot
```

#### 2. Configure Discord OAuth

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Copy the **Client ID**
3. Set OAuth2 Redirect URL to `http://localhost:3000`
4. Create a client secret and store it securely

#### 3. Set Environment Variables

Create a `.env` file in the project root with your credentials:

```env
DISCORD_CLIENT_ID=your-client-id
DISCORD_REDIRECT_URI=http://localhost:3000
DB_PASSWORD=your-secure-password
PGADMIN_PASSWORD=your-pgadmin-password
GRAFANA_ADMIN_PASSWORD=your-grafana-password
```

#### 4. Start Services

```bash
docker compose up --build
```

Services will be available at:

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Frontend | http://localhost:3000 | N/A |
| API | http://localhost:8001 | Bearer token auth |
| PgAdmin | http://localhost:5050 | admin@example.com / admin123 |
| Grafana | http://localhost:3002 | admin / admin123 |
| Redis Commander | http://localhost:8081 | N/A |

## First Steps

### 1. Access the Frontend

Navigate to http://localhost:3000 and click "Sign in with Discord" to authenticate using OAuth.

### 2. View Your Profile

Once authenticated, you'll see:
- Your Discord profile information
- Connected accounts
- Data managed by Winter Dragon

### 3. Monitor the Database

Visit http://localhost:5050 (PgAdmin) to manage the PostgreSQL database directly.

### 4. View Analytics

Visit http://localhost:3002 (Grafana) to view database analytics and logs using the pre-configured PostgreSQL datasource.

## Troubleshooting

### Services Won't Start

Check logs:
```bash
docker compose logs -f
```

### Database Connection Issues

Verify PostgreSQL is healthy:
```bash
docker compose ps
```

### OAuth Not Working

1. Verify `DISCORD_CLIENT_ID` is correct
2. Check OAuth Redirect URL matches `DISCORD_REDIRECT_URI`
3. Ensure frontend is accessible at the configured URL
