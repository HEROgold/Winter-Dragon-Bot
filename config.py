class main:
    prefix = "$"
    show_logged_in = True
    log_messages = True
    token="TOKEN"
    owner_id= YourUserId

class error: # Wether or not to log and message when error is hit.
    ignore_errors               = False
    log_MissingRequiredArgument = True
    log_BotMissingPermissions   = True
    log_CommandNotFound         = True
    log_MissingPermissions      = True
    log_TooManyArguments        = True
    log_PrivateMessageOnly      = True
    log_NoPrivateMessage        = True
    log_HTTPException           = True
    log_CommandError            = True

class purge:
    limit = 50 # Limit amount of total messaged to be purged.
    ratelimit_amount = 1 # Amount of times command can be used
    ratelimit_seconds = 60 # Seconds of time before ratelimit_amount is reset.

class reminder:
    min_duration = 1 # Minutes, Default and min 1
    max_duration = 365 # Days, Default and max 365

class welcome:
    dm_user = True

class poll:
    time = "1d" # Default time added under the poll to display when it is finished in: Default "1d"
    # Format: d = days, h = hours, m = minutes, s = seconds. Set to 0s to remove.

class announcement:
    mention_all = True

class urban:
    allow_random = True
    max_length = 3 # Maximum 10

class invite:
    dm_user = True # Dm user INSTEAD of sending message to the current chat.
