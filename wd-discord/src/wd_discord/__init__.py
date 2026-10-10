"""wd-discord: a small Discord API (v10) client library for Winter Dragon.

The names here are the high-level API: entities bound to a :class:`Client` (``User``, ``Channel``,
``Interaction``, ...) that act without passing the client around. The pydantic data models they wrap
keep the Discord docs' names in their own modules (``wd_discord.resources``, ``wd_discord.gateway.events``).
"""

from __future__ import annotations

lazy from wd_config.discord import URLS

lazy from wd_discord.audit import AuditLogReason
lazy from wd_discord.authenticate import Token, TokenType
lazy from wd_discord.client import Client, NetworkError, is_network_error
lazy from wd_discord.embed import Embed, EmbedField
lazy from wd_discord.entities import (
    AnyInteraction,
    Application,
    AutocompleteInteraction,
    BoundEvent,
    Channel,
    CommandInteraction,
    ComponentInteraction,
    CurrentUser,
    Emoji,
    Entitlement,
    GatewayGuild,
    GlobalCommand,
    Guild,
    GuildCommand,
    Interaction,
    Invite,
    Member,
    Message,
    PartialChannel,
    PartialGlobalCommand,
    PartialGuild,
    PartialGuildCommand,
    PartialMember,
    PartialMessage,
    PartialRole,
    PartialUser,
    PermissionOverwrite,
    Ready,
    Resolved,
    Role,
    Sticker,
    Team,
    TeamMember,
    ThreadMember,
    UnknownInteraction,
    User,
    VoiceState,
    bind,
)
lazy from wd_discord.errors import ApiResponseError
lazy from wd_discord.gateway import (
    EventName,
    Gateway,
    GatewayActivity,
    GatewayBotInfo,
    GuildCreate,
    RawEvent,
    ShardManager,
    Status,
)
lazy from wd_discord.models import DiscordModel
lazy from wd_discord.partial_emoji import PartialEmoji
lazy from wd_discord.permissions import ChannelType, Permissions
lazy from wd_discord.sentry import Sentry
lazy from wd_discord.snowflake import Snowflake


__all__ = [
    "URLS",
    "AnyInteraction",
    "ApiResponseError",
    "Application",
    "AuditLogReason",
    "AutocompleteInteraction",
    "BoundEvent",
    "Channel",
    "ChannelType",
    "Client",
    "CommandInteraction",
    "ComponentInteraction",
    "CurrentUser",
    "DiscordModel",
    "Embed",
    "EmbedField",
    "Emoji",
    "Entitlement",
    "EventName",
    "Gateway",
    "GatewayActivity",
    "GatewayBotInfo",
    "GatewayGuild",
    "GlobalCommand",
    "Guild",
    "GuildCommand",
    "GuildCreate",
    "Interaction",
    "Invite",
    "Member",
    "Message",
    "NetworkError",
    "PartialChannel",
    "PartialEmoji",
    "PartialGlobalCommand",
    "PartialGuild",
    "PartialGuildCommand",
    "PartialMember",
    "PartialMessage",
    "PartialRole",
    "PartialUser",
    "PermissionOverwrite",
    "Permissions",
    "RawEvent",
    "Ready",
    "Resolved",
    "Role",
    "Sentry",
    "ShardManager",
    "Snowflake",
    "Status",
    "Sticker",
    "Team",
    "TeamMember",
    "ThreadMember",
    "Token",
    "TokenType",
    "UnknownInteraction",
    "User",
    "VoiceState",
    "bind",
    "is_network_error",
]
