from pathlib import Path
from urllib import parse

import discord


PROJECT_DIR = Path(__file__).parent.parent
BOT_DIR = Path(__file__).parent
DYNAMIC_DIR = BOT_DIR / "dynamic"
IMG_DIR = DYNAMIC_DIR / "img"
EMOJI_DIR = DYNAMIC_DIR / "emoji"

BOT_CONFIG = BOT_DIR / "config.ini"
EXTENSIONS = BOT_DIR / "extensions"
METRICS_FILE = IMG_DIR / "system_metrics.png"

BOT_PERMISSIONS = 70368744177655 # All bot permissions

V10 = "https://discord.com/api/v10"
OAUTH2 = "https://discord.com/api/oauth2"
DISCORD_AUTHORIZE = f"{OAUTH2}/authorize"
DISCORD_OAUTH_TOKEN = f"{OAUTH2}/token"
SERVER_IP = "localhost"
WEBSITE_PORT = 80
WEBSITE_URL = f"http://{SERVER_IP}:{WEBSITE_PORT}"
GET_TOKEN_WEBSITE_URL = parse.quote(f"{WEBSITE_URL}/get_token")
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
BOT_SCOPE = [
    "bot",
]

DATE_FORMAT = "%Y-%m-%d, %H:%M:%S"
CURRENCY_LABELS = "-$€£¥₣₹د.كد.ك﷼₻₽₾₺₼₸₴₷฿원₫₮₯₱₳₵₲₪₰()"

# Urban Dictionary API
UD_RANDOM_URL = "http://api.urbandictionary.com/v0/random"
UD_DEFINE_URL = "http://api.urbandictionary.com/v0/define?term="

# Steam
DISCOUNT_FINAL_PRICE = "discount_final_price"
DISCOUNT_PERCENT = "discount_pct"
SEARCH_GAME_TITLE = "title"
DATA_APPID = "data-ds-appid"
DISCOUNT_PRICES = "discount_prices"
GAME_BUY_AREA = "game_area_purchase_game_wrapper"
SINGLE_GAME_TITLE = "apphub_AppName"
GAME_RELEVANT = "block responsive_apppage_details_right heading responsive_hidden"
IS_DLC_RELEVANT_TO_YOU = "Is this DLC relevant to you?"
BUNDLE_TITLE = "pageheader"
BUNDLE_LINK = "tab_item_overlay"
BUNDLE_PRICE = "price bundle_final_package_price"
BUNDLE_DISCOUNT = "price bundle_discount"
BUNDLE_FINAL_PRICE = "price bundle_final_price_with_discount"
STEAM_SEND_PERIOD = 3600 * 3 # 3 hour cooldown on updates in seconds
STEAM_PERIOD = STEAM_SEND_PERIOD * 10

# Bot Status Messages
STATUS_MSGS = [
    "Licking a wedding cake",
    "Eating a wedding cake",
    "Comparing wedding cakes",
    "Taste testing a wedding cake",
    "Crashing a wedding to eat their cake",
    "Getting married to eat a cake",
    "Throwing a wedding cake",
    "Devouring a wedding cake",
    "Sniffing wedding cakes",
    "Touching a wedding cake",
    "Magically spawning a wedding cake",
    "Wanting to eat a wedding cake and have one too",
]


# Message Reasons
AUTO_ASSIGN_REASON = "Member joined, AutoAssign"
AUTOCHANNEL_CREATE_REASON = "Creating AutomaticChannel"

# Logs channels
LOG_CHANNEL_NAME = "LOG-CATEGORY"
MEMBER_UPDATE_PROPERTIES = [
    "nick",
    "roles",
    "pending",
    "guild_avatar",
    "guild_permissions",
]
MAX_CATEGORY_SIZE = 50
CREATED_COLOR = 0x00FF00
CHANGED_COLOR = 0xFFFF00
DELETED_COLOR = 0xFF0000

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
