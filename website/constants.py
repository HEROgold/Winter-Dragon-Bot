from pathlib import Path


WEBSITE_DIR = Path(__file__).parent

WEBSITE_CONFIG = WEBSITE_DIR / "config.ini"

WEBSITE_URL = ""
APPLICATION_ID = 0
OAUTH2 = "https://discord.com/api/oauth2"
DISCORD_AUTHORIZE = f"{OAUTH2}/authorize"
OAUTH_SCOPE = [
    "relationships.read",
    "guilds.members.read",
    "connections",
    "email",
    "activities.read",
    "identify",
    "guilds",
    "applications.commands",
    "applications.commands.permissions.update",
]
