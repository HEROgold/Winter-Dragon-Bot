class main:
    prefix:str = "$" # default prefix, bot can also just be mentioned.
    show_logged_in:bool = True
    log_messages:bool = False # Seems to not work, even with Discord.Intents.message turned ON
    token:str = "123456789" # your discord bot token!
    enable_custom_help:bool = True # Enable custom help command! (Preferred)
    use_database:bool = True # Use MongoDatabase instead of json files
    database_name:str = "winter_dragon" # Name of the MongoDatabase

class database:
    IP_PORT:str = "localhost:27017"
    USER_PASS:str = "user:pass"
    AUTH_METHOD:str = "SCRAM-SHA-256"

class activity:
    # Change the variable in cogs\extension\activity.py for more options
    random_activity:bool = True # Allow random activity on startup
    periodic_change:bool = True # Rotate through random activities/Status when true
    periodic_time:int = 180 # Time to swtich between activities and Status (Keep the time reasonable to not get ratelimit blocked)

class autochannel:
    clean_timer:int = 60*60 # Time in seconds how often to clean autochannels Set to 0 to clean once on startup.

class message:
    limit = 100 # Limit of messages to gather when command is used.
class help:
    max_per_page:int = 15 # Set max amount of commands shown per help page. Discord has a maximum of 25 fields per embed.

class rpg:
    fix:bool = True

class steam:
    url:str = "https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1"

class translate:
    api_key:str = "OpenAI api key" # OpenAI api key
    dm_instead:bool = True # Send translated message in a DM instead of normal channel (Preferred)
    limit:int = 500 # Limit the amount of characters/tokens used for the translation

class team:
    dm_insteadp:bool = True # Send a DM to the user when sending notifications

class ban:
    default_bantime:int = 28800 # This is in seconds. 60 is a minute, 3600 is an hour etc.
    rolename:str = "Banned"

class error: # Wether or not to log and message when error is hit.
    ignore_errors:bool = False # Makes the bot ignore unhandled errors.
    always_log_errors:bool = True # Always send log messages in log file
    MissingRequiredArgument:bool = True
    BotMissingPermissions:bool = True
    CommandNotFound:bool = True
    MissingPermissions:bool = True
    TooManyArguments:bool = True
    PrivateMessageOnly:bool = True
    NoPrivateMessage:bool = True
    HTTPException:bool = True
    CooldownError:bool = True
    CheckFailure:bool = True
    DisabledCommand:bool = True
    UserMissingRole:bool = True
    UserMissingRole:bool = True
    CommandInvokeError:bool = True
    NotOwner:bool = True

class purge:
    limit:int = 1000 # Limit amount of total messaged to be purged.
    ratelimit_amount:int = 1 # Amount of times command can be used
    ratelimit_seconds:int = 60 # Seconds of time before ratelimit_amount is reset.
    use_history_instead:bool = False # use message history instead of purge. WARNING: This might cause ratelimits!

class reminder:
    min_duration:bool = 1 # Minutes, Default and min 1
    max_duration:bool = 365 # Days, Default and max 365

class welcome:
    dm_user:bool = True

class announcement:
    mention_all:bool = True

class urban:
    allow_random:bool = True
    max_length:int = 5 # Maximum 10
