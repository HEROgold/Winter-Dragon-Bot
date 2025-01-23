from pathlib import Path


WEBSITE_DIR = Path(__file__).parent

WEBSITE_CONFIG = WEBSITE_DIR / "config.ini"

WEBSITE_URI = ""  # The URI that links to this website, or the ip of the server.
APPLICATION_ID = 1226868250713784331
"""The application ID related to the bot."""
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
