# Getting Started

This guide gets your own Winter Dragon instance (the `v2` branch) running in a Discord server.

## 1. Create the Discord application

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and
   add a bot to it.
2. Copy the bot token. Treat it like a password.
3. Under **Bot → Privileged Gateway Intents**, enable the message-content intent if you want message logging.

## 2. Install and configure

```bash
git clone https://github.com/HEROgold/Winter-Dragon-Bot.git
cd Winter-Dragon-Bot
git checkout v2
uv sync
uv run python -m winter_dragon.run_test_bot
```

The first run writes `config.ini` and `discord.ini` and stops. Open `config.ini` and replace every `!!` value,
at least `[Tokens] discord_token`. Then run the command again. `run_test_bot` uses a local sqlite database and
stops after 10 minutes, which is enough to check that everything works.

To run the bot for real, start PostgreSQL and use the main entry point:

```bash
docker compose up -d postgres redis
uv run python -m winter_dragon
```

## 3. Invite the bot

Once the bot is online, use `/invite bot` for an invite link. The bot syncs its slash commands with Discord when
it starts, and they appear in your server shortly after.

## Commands

| Command | What it does |
|---|---|
| `/fuel add`, `/fuel efficiency` | Log refuels and graph your fuel efficiency. |
| `/reminder add`, `/reminder repeat`, `/reminder remove` | One-off and repeating reminders. |
| `/steam ...` | Get notified about free and discounted Steam games. |
| `/urban search`, `/urban random` | Look up words on Urban Dictionary. |
| `/love` | Calculate your compatibility with another user. |
| `/uptime bot` | How long the bot has been running. |
| `/invite bot`, `/invite guild` | Invite the bot, or join its support server. |
| `/bot-commands ...` | Admin only (Manage Server): inspect and resync the bot's commands. |

Everything the `main` branch offers, and what has been ported to `v2` so far, is listed in the
[Feature Inventory](../features/index.md).

## Troubleshooting

- **The bot stops with `FirstTimeLaunchError`:** `config.ini` still contains `!!` values. Fill them in.
- **Import error mentioning psycopg:** `python -m winter_dragon` needs PostgreSQL and its driver. Use
  `run_test_bot` for a sqlite instance instead.
- **Commands don't show up:** check the bot's log in `logs/` for sync errors, then run `/bot-commands` as an
  admin.
