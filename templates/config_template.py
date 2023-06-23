import logging


class Tokens:
    DISCORD_TOKEN: str = "KEY" # your discord bot token!
    OPEN_API_KEY: str = "KEY" # OpenAI API Key

class Main:
    BOT_NAME: str = "NAME" # Name of the bot and database
    PREFIX: str = "$" # default prefix, bot can also just be mentioned.
    SHOW_LOGGED_IN: bool = True # Show message when logged in.
    LOG_MESSAGES: bool = False # Seems to not work, even with Discord.Intents.message turned ON
    CUSTOM_HELP: bool = True # Enable custom help command! (Preferred)
    USE_DATABASE: bool = True # Use Sql instead of files
    SUPPORT_GUILD_ID: int = 765965358754037801 # Guild id of the bot's support guild
    LOG_LEVEL: logging = "DEBUG" # CRITICAL = 50, FATAL = CRITICAL, ERROR = 40, WARNING = 30, WARN = WARNING, INFO = 20, DEBUG = 10, NOTSET = 0
    LOG_PATH: str = "./logs" # Path where logs are saved.
    LOG_SIZE_KB_LIMIT: int = 3 * 1000 * 1000 # Size in Bytes of how much to keep. removes oldest logs first when hitting the limit.
    KEEP_LATEST_LOGS: bool = False

class Gameservers:
    BACKGROUND = True # Start new processes in background of computer (no popup windows)
    ALLOWED = [] # list of user id's allowed to use gameserver commands

class Database:
    PERIODIC_CLEANUP: bool = True # allow periodic cleanups of the database (mongodb or the file's)
    IP_PORT: str = "IP:PORT"
    USER_PASS: str = "USERNAME:PASSWORD"
    AUTH_METHOD: str = "SCRAM-SHA-256"

class Activity:
    RANDOM_ACTIVITY: bool = True # Allow random activity on startup
    PERIODIC_CHANGE: bool = True # Rotate through random activities/Status when true
    PERIODIC_TIME: int = 180 # Time to switch between activities and Status (Keep the time reasonable to not get rate limit blocked)

class Autochannel:
    AUTOCHANNEL_NAME = "AutoChannel"

class Message:
    LIMIT = 100 # Limit of messages to gather when command is used.

class Help:
    PAGE_MAX: int = 15 # Set max amount of commands shown per help page. Discord has a maximum of 25 fields per embed.

class Steam:
    # Steam url to scrape from with search parameters.
    URL: str = "https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1&supportedlang=english"

class Translate:
    DM_INSTEAD: bool = True # Send translated message in a DM instead of normal channel (Preferred)
    LIMIT: int = 500 # Limit the amount of characters/tokens used for the translation

class Team:
    DM_INSTEAD: bool = True # Send a DM to the user when sending notifications

class Ban:
    DEFAULT_BANTIME: int = 28800 # This is in seconds. 60 is a minute, 3600 is an hour etc.
    ROLENAME: str = "TempBanned"

class Error: # Wether or not to log and message when error is hit.
    ALWAYS_LOG_ERRORS: bool = True # Always send log messages in log file
    IGNORE_ERRORS: bool = False # Makes the bot ignore unhandled errors.

class Purge:
    LIMIT: int = 100 # Limit amount of total messaged to be purged.
    RATELIMIT_AMOUNT: int = 1 # Amount of times command can be used
    RATELIMIT_SECONDS: int = 60 # Seconds of time before ratelimit_amount is reset.
    USE_HISTORY: bool = False # use message history to followup after purge WARNING: This might cause ratelimits!

class Reminder:
    MIN_DURATION: int = 1 # Minutes, Default and min 1
    MAX_DURATION: int = 365 # Days, Default and max 365

class Welcome:
    DM: bool = True # DM the user instead of putting it in the public chat

class Announcement:
    MENTION_ALL: bool = True

class Urban:
    ALLOW_RANDOM: bool = True
    MAX_LENGTH: int = 5 # Maximum 10
