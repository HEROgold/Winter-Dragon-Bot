"""Constants used throughout the library."""
from __future__ import annotations


DISCORD_EPOCH = 1420070400000
RATE_LIMIT_BUCKET = "X-RateLimit-Bucket"
"""It's recommended to use this header as a unique identifier for a rate limit,
which will allow you to group shared limits as you encounter them."""
