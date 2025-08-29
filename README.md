# Winter-Dragon-Bot

## Description

Winter-Dragon-Bot is a versatile Discord bot project with multiple components designed to enhance server management, provide entertainment, and offer a wide range of utilities. The project includes a bot, database, backend API, and frontend web interface. Built with Python 3.13 and leveraging PostgreSQL for data management, this project helps with continuous learning and improvement in software development.

## Project Structure

```dir
Winter-Dragon-Bot/
├── bot/                  # Discord bot implementation
├── database/             # Database models and schemas
├── backend/              # FastAPI backend service
├── frontend/             # Web interface (Bun.js)
├── docker-compose.yml    # Docker configuration
└── README.md             # Project documentation
```

## Features

### Bot

see [Bot](docs/bot/features.md) for more details.

- **Moderation & Administration**

  - Channel management with auto-channels
  - Role management with auto-assignment
  - Welcome system with customizable messages
  - Ban synchronization across servers
  - Infractions tracking system
  - Gatekeeper for server access control
  - Message purging with rate limits
  - Logging system for different actions

- **Utility Features**

  - Reminders with customizable durations
  - Server and user statistics tracking
  - Comprehensive audit logging
  - Performance monitoring
  - Car fuel consumption tracking

- **Entertainment**

  - Various text based games (hangman, "would you rather", etc.)
  - Game/voice lobby creation and management
  - Looking for group functionality for multiple games

- **Technical Features**

  - Error handling
  - Performance metrics collection

### Frontend

see [Frontend](docs/frontend/features) for more details.

### Database

see [Database](docs/database/features) for more details.

### Additional Features

- **Advanced Configuration**: Customizable settings through a config file
- **Dynamic Logging**: Separate logs for different aspects
- **Docker Support**: Containerized for easy deployment and scalability
- **Web Interface**: Browser-based management

## Installation

### Prerequisites

- Docker and Docker Compose installed on your system
- A Discord Bot Token (from Discord Developer Portal)

### Steps

1. **Clone the Repository**: Clone this repository to your local machine using `git clone`.
1. **Initial Configuration**: After the first run, modify the `config.ini` file with your Discord Bot Token.
1. **Docker Setup**: Navigate to the project directory and run `docker compose build` to build the containers. Use `docker compose up -d` to start the entire project.
1. **Verify Installation**: The bot should connect to Discord and the website should become available.

### Starting the Bot

The easiest way to run Winter-Dragon-Bot is using Docker Compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop all services
docker-compose down
```

This will start all required services:

- PostgreSQL database
- Discord bot
- FastAPI backend
- Web frontend

### Notes

1. Using Docker is recommended for production environments for a streamlined and consistent deployment.
1. All components run in separate containers but share a network for inter-service communication.
1. Data is persisted using Docker volumes for the database.

## API Reference

<!-- TODO -->

The backend provides the following API endpoints:

| Endpoint                 | Method   | Description                    |
| ------------------------ | -------- | ------------------------------ |
| `/api/bot/status`        | GET      | Get current bot status         |
| `/api/bot/commands`      | GET      | List all available commands    |
| `/api/bot/guilds`        | GET      | List all guilds the bot is in  |
| `/api/guilds/{guild_id}` | GET      | Get specific guild information |
| `/api/settings`          | GET/POST | Get/Update bot settings        |
| `/api/users`             | GET      | Get users data                 |
| `/api/audit-logs`        | GET      | Get audit logs                 |

## Contributing

Contributions to Winter-Dragon-Bot are always welcome, whether it be improvements to the codebase, bug reports, or new features. Please feel free to fork the repository and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Work In Progress

Some parts of the bot might be a work in progress.

The bot itself has a dedicated extension directory for those extensions.
Extensions inside this directory are not or not fully tested.

There's also the website that needs to be worked on.
This should contain pages to manage bot settings more easily and might have **all** users be able to log in.
The website doesn't have any finalized decisions, and is currently in alpha stage. Anything can and will change.

## Dev-requirements

While working on this project, make sure to add the src files of the sub-projects (bot, database, backend)
to your editor's path.

### .vscode/settings.json

Setup vscode to allow for correct importing of the other modules.

```json
    "python.analysis.extraPaths": [
        "${workspaceFolder}/database/src",
        "${workspaceFolder}/bot/src",
        "${workspaceFolder}/backend/src"
    ],
    "python.autoComplete.extraPaths": [
        "${workspaceFolder}/database/src",
        "${workspaceFolder}/bot/src",
        "${workspaceFolder}/backend/src"
    ],
```

## Development

Because this project contains 3 modules under the namespace winter_dragon, you'll need to set up a development environment:

1. **Set up your environment with UV**:

   ```bash
   # Install UV if you don't have it
   curl -fsSL https://raw.githubusercontent.com/astral-sh/uv/main/install.sh | bash

   # Create a virtual environment
   uv venv

   # Activate the virtual environment
   # On Unix/macOS
   source .venv/bin/activate
   # On Windows
   .venv\Scripts\activate
   ```

1. **Install development dependencies**:

   ```bash
   # Install all project components in development mode
   uv pip install -e ./database -e ./bot -e ./backend
   ```

1. **Run components**:

   ```bash
   # Run the bot
   python -m winter_dragon.bot

   # Run the backend (in a separate terminal)
   python -m winter_dragon.backend
   ```

### Creating New Extensions

To create a new bot extension:

1. Create a new Python file or directory in `bot/src/winter_dragon/bot/extensions/`
1. Implement the extension using the Cog or GroupCog pattern from WinterDragon
1. Add an async `setup` function that adds the cog to the bot
