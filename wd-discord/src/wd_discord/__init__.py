"""wd-discord: a small Discord API (v10) client library for Winter Dragon."""
from __future__ import annotations

from wd_config.discord import URLS

from wd_discord.authenticate import Token, TokenType
from wd_discord.client import Client
from wd_discord.errors import ApiResponseError
from wd_discord.gateway import Gateway, GatewayActivity, GatewayBotInfo, Ready, ShardManager, Status
from wd_discord.permissions import ChannelType, Permissions
from wd_discord.snowflake import Snowflake


__all__ = [
    "URLS",
    "ApiResponseError",
    "ChannelType",
    "Client",
    "Gateway",
    "GatewayActivity",
    "GatewayBotInfo",
    "Permissions",
    "Ready",
    "ShardManager",
    "Snowflake",
    "Status",
    "Token",
    "TokenType",
]
