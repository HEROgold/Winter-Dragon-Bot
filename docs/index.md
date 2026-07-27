# Welcome to Winter Dragon

**Winter Dragon** is a versatile Discord bot with moderation, utility, and entertainment features. This documentation covers user guides, API reference, and development information.

## Features

- **Moderation Tools**: Comprehensive moderation commands and automation
- **Utility Functions**: Helpful utility commands for Discord servers
- **Entertainment**: Games and fun features for community engagement
- **User Dashboard**: Authenticated view with Discord OAuth integration
- **REST API**: FastAPI-powered backend for programmatic access
- **Monitoring**: Grafana dashboards for logs and database analytics

## Quick Start

### Running with Docker

```bash
export DISCORD_CLIENT_ID="your-client-id"
export DISCORD_REDIRECT_URI="http://localhost:3000"
docker compose up --build
```

### Available Services

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8001
- **PgAdmin**: http://localhost:5050
- **Grafana**: http://localhost:3002
- **Redis Commander**: http://localhost:8081

## Documentation Structure

- **[Feature Inventory](features/index.md)** — Every capability the bot offers on `main`, with v2 porting status
- **[User Guide](guide/getting-started.md)** — How to use the bot and access the dashboard
- **[Development](dev/architecture.md)** — Architecture, setup, and technical details
- **[API Reference](api-reference.md)** — REST API endpoints and authentication

## Technology Stack

- **Frontend**: React + Bun (TSRX)
- **Backend**: FastAPI with SQLModel ORM
- **Database**: PostgreSQL
- **Cache**: Redis
- **Discord Integration**: discord.py
- **Analytics**: Grafana + PostgreSQL
- **Admin Panel**: PgAdmin
- **Containerization**: Docker & Docker Compose

## Contributing

Contributions are welcome! Please refer to the development guides for setup instructions and architecture documentation.

## License

This project is licensed under the MIT License. See [LICENSE.md](https://github.com/HEROgold/Winter-Dragon-Bot/blob/v2/LICENSE.md) for details.
