"""Every config scope's ini file, declared once.

Each scope binds its file from here, and the legacy ``config.ini`` migration names the same files. Importing this
module binds nothing, so the migration can name a file before its scope reads or writes it.
"""

lazy from pathlib import Path


APP_CONFIG_FILE = Path("config.ini")
"""The app-wide settings."""
COGS_CONFIG_FILE = Path("cogs.ini")
"""The cogs' settings, one section per settings class."""
BOT_CONFIG_FILE = Path("bot.ini")
"""wd-bot's settings and tokens."""
DATABASE_CONFIG_FILE = Path("database.ini")
"""wd-db's settings."""
DASHBOARD_CONFIG_FILE = Path("dashboard.ini")
"""The web dashboard's settings; only the web process binds it."""
ARCHIVE_CONFIG_FILE = Path("archive.ini")
"""The archive gateway's settings."""
DISCORD_CONFIG_FILE = Path("discord.ini")
"""wd-config's internal Discord settings."""
SENTRY_CONFIG_FILE = Path("sentry.ini")
"""wd-config's Sentry settings."""
