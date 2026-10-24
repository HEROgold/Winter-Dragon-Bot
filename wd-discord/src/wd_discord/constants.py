"""Constants used throughout the library."""


DISCORD_EPOCH = 1420070400000
"""The first millisecond of 2015, in Unix milliseconds: the epoch of Discord's snowflakes (https://docs.discord.com/developers/reference#snowflakes)."""
RATE_LIMIT_BUCKET = "X-RateLimit-Bucket"
"""It's recommended to use this header as a unique identifier for a rate limit,
which will allow you to group shared limits as you encounter them
(https://docs.discord.com/developers/topics/rate-limits#header-format)."""
