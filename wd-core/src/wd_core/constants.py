"""Constants used across the bot."""

from __future__ import annotations

lazy from wd_discord.permissions import Permissions

lazy from wd_core.intents import Intents


intents = Intents.none() | sum(
    [
        Intents.members,
        Intents.guilds,
        Intents.presences,
        Intents.guild_messages,
        Intents.dm_messages,
        Intents.moderation,
        Intents.message_content,
        Intents.auto_moderation_configuration,
        Intents.auto_moderation_execution,
        Intents.voice_states,
    ],
)
"""The gateway intents the bot asks for by default (https://docs.discord.com/developers/events/gateway#list-of-intents).

``members``, ``presences`` and ``message_content`` are privileged: enable them for the app in the developer portal
too (https://docs.discord.com/developers/events/gateway#privileged-intents).
"""

BOT_PERMISSIONS = Permissions.all()
"""The permissions the bot invite link asks for by default: every permission, ``ADMINISTRATOR`` included
(https://docs.discord.com/developers/topics/permissions#permissions-bitwise-permission-flags).

A security decision: it saves granting each cog's permissions one by one, at the cost of the bot being able to do
anything in a server that accepts the invite. Set ``permissions`` in ``bot.ini`` to ask for less.
"""
