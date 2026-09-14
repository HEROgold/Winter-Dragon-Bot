"""wd-discord: a small Discord API (v10) client library for Winter Dragon."""

from __future__ import annotations

lazy from wd_config.discord import URLS

lazy from wd_discord.authenticate import Token, TokenType
lazy from wd_discord.client import Client
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.errors import ApiResponseError
lazy from wd_discord.gateway import (
    EventName,
    Gateway,
    GatewayActivity,
    GatewayBotInfo,
    GuildCreate,
    Message,
    RawEvent,
    Ready,
    ShardManager,
    Status,
)
lazy from wd_discord.models import DiscordModel
lazy from wd_discord.partial_emoji import PartialEmoji
lazy from wd_discord.permissions import ChannelType, Permissions
lazy from wd_discord.resources.application import Application
lazy from wd_discord.resources.channel import Channel
lazy from wd_discord.resources.guild import Guild
lazy from wd_discord.resources.invite import Invite
lazy from wd_discord.resources.user import User
lazy from wd_discord.sentry import Sentry
lazy from wd_discord.snowflake import Snowflake


__all__ = [
    "URLS",
    "ApiResponseError",
    "Application",
    "Channel",
    "ChannelType",
    "Client",
    "DiscordModel",
    "Embed",
    "EmbedField",
    "EventName",
    "Gateway",
    "GatewayActivity",
    "GatewayBotInfo",
    "Guild",
    "GuildCreate",
    "Invite",
    "Message",
    "PartialEmoji",
    "Permissions",
    "RawEvent",
    "Ready",
    "Sentry",
    "ShardManager",
    "Snowflake",
    "Status",
    "Token",
    "TokenType",
    "User",
]
