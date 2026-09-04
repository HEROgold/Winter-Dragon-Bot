"""Constants used across the bot."""
from __future__ import annotations

from wd_core.intents import Intents


intents = Intents.none() | sum([
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
])

BOT_PERMISSIONS = Permissions.all()
