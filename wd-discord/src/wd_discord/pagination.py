"""Pagination utilities for the Discord API.

https://docs.discord.com/developers/reference#snowflake-ids-in-pagination
"""
from __future__ import annotations

from wd_discord.constants import DISCORD_EPOCH


def snowflake_from_timestamp(timestamp: int) -> int:
    """Convert a Discord snowflake timestamp to a Snowflake timestamp."""
    return (timestamp - DISCORD_EPOCH) << 22
