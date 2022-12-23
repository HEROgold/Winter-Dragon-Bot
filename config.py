class main:
    prefix:str = "$" # default prefix, bot can also just be mentioned.
    show_logged_in:bool = True
    log_messages:bool = False # Seems to not work, even with Discord.Intents.message turned ON
    token:str = "" # your discord bot token!
    owner_id:int = 0 # your discord user id!
    enable_custom_help:bool = True # Enable custom help command! (Preferred)

class activity:
    # Change the variable in cogs\extension\activity.py for more options
    random_activity:bool = True # Allow random activity on startup
    periodic_change:bool = True # Rotate through random activities/Status when true
    periodic_time:int = 180 # Time to swtich between activities and Status (Keep the time reasonable to not get ratelimit blocked)

class help:
    max_per_page:int = 15 # Set max amount of commands shown per help page. Discord has a maximum of 25 fields per embed.

class rpg:
    fix:bool = True

class steam:
    url:str = "https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1"

class translate:
    api_key:str = ""
    dm_instead:bool = True # Send translated message in a DM instead of normal channel (Preferred)
    limit:int = 500 # Limit the amount of characters/tokens used for the translation

class team:
    dm_insteadp:bool = True # Send a DM to the user when sending notifications

class ban:
    default_bantime:int = 28800 # This is in seconds. 60 is a minute, 3600 is an hour etc.
    rolename:str = "Banned"

class wyr: # These settings also apply to the Never Have I Ever questions.
    delete_command:bool = False # Delete the message that called the wyr command
    dm_instead:bool = True # Dm user when they add a question INSTEAD of sendint it to channel.

class error: # Wether or not to log and message when error is hit.
    ignore_errors:bool = False # Makes the bot ignore unhandled errors.
    always_send_errors:bool = False # Always send error when true, in dm.
    log_MissingRequiredArgument:bool = True
    log_BotMissingPermissions:bool = True
    log_CommandNotFound:bool = True
    log_MissingPermissions:bool = True
    log_TooManyArguments:bool = True
    log_PrivateMessageOnly:bool = True
    log_NoPrivateMessage:bool = True
    log_HTTPException:bool = True
    log_CooldownError:bool = True
    log_CheckFailure:bool = True
    log_DisabledCommand:bool = True
    log_UserMissingRole:bool = True
    log_UserMissingRole:bool = True

class purge:
    limit:int = 50 # Limit amount of total messaged to be purged.
    ratelimit_amount:int = 1 # Amount of times command can be used
    ratelimit_seconds:int = 60 # Seconds of time before ratelimit_amount is reset.
    delete_after:int = 10 # Delete notification message after X seconds

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

class invite:
    dm_user:bool = True # Dm user INSTEAD of sending message to the current chat.