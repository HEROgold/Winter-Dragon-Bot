"""wd-discord: a small Discord API (v10) client library for Winter Dragon."""
from __future__ import annotations

from wd_config.discord import URLS

from wd_discord.application import Application
from wd_discord.authenticate import Token, TokenType
from wd_discord.channel import Channel
from wd_discord.client import Client
from wd_discord.errors import ApiResponseError
from wd_discord.gateway import Gateway, GatewayActivity, GatewayBotInfo, Ready, ShardManager, Status
from wd_discord.guild import Guild
from wd_discord.models import DiscordModel
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.permissions import ChannelType, Permissions
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


__all__ = [
    "URLS",
    "ApiResponseError",
    "Application",
    "Channel",
    "ChannelType",
    "Client",
    "DiscordModel",
    "Gateway",
    "GatewayActivity",
    "GatewayBotInfo",
    "Guild",
    "PartialEmoji",
    "Permissions",
    "Ready",
    "ShardManager",
    "Snowflake",
    "Status",
    "Token",
    "TokenType",
    "User",
]
