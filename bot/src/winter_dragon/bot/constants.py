"""Module to contain the constants used in the WinterDragon project."""

from pathlib import Path

import discord


CWD = Path.cwd()

PACKAGE_DIR = Path(__file__).parent
ROOT_DIR = PACKAGE_DIR.parent
DYNAMIC_DIR = PACKAGE_DIR / "dynamic"
IMG_DIR = DYNAMIC_DIR / "img"
EMOJI_DIR = DYNAMIC_DIR / "emoji"
EXTENSIONS = PACKAGE_DIR / "extensions"
METRICS_FILE = IMG_DIR / "system_metrics.png"
BOT_CONFIG = CWD / "config.ini"

BOT_PERMISSIONS = 70368744177655 # All bot permissions

V10 = "https://discord.com/api/v10"
OAUTH2 = "https://discord.com/api/oauth2"
DISCORD_AUTHORIZE = f"{OAUTH2}/authorize"
DISCORD_OAUTH_TOKEN = f"{OAUTH2}/token"
# unused GET_TOKEN_WEBSITE_URL = parse.quote(f"{Settings.WEBSITE_URL}/get_token")

# Urban Dictionary API
UD_RANDOM_URL = "http://api.urbandictionary.com/v0/random"
UD_DEFINE_URL = "http://api.urbandictionary.com/v0/define?term="

# Discord Intents
INTENTS = discord.Intents.none()
INTENTS.members = True
INTENTS.guilds = True
INTENTS.presences = True
INTENTS.guild_messages = True
INTENTS.dm_messages = True
INTENTS.moderation = True
INTENTS.message_content = True
INTENTS.auto_moderation_configuration = True
INTENTS.auto_moderation_execution = True
INTENTS.voice_states = True
GUILD_OWNERSHIP_LIMIT = 10


## ensure directories exist

DYNAMIC_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)
EMOJI_DIR.mkdir(exist_ok=True)
WEEKS_IN_MONTH = 52
