# Typed @overload signatures for wd_discord.gateway.dispatch.parse_dispatch.
#
# GENERATED FILE - do not hand-edit. Regenerate with:
#
#     uv run wd-discord/scripts/generate_dispatch_overloads.py
#
# One overload per EventName member that has a model wired up (EventName.X.model is not None) -
# see generate_dispatch_overloads.py for why members without a model
# aren't listed here individually (they already resolve fine through the general fallback below).
# (no module docstring here on purpose - ruff's PYI021 flags docstrings in stub files)

from collections.abc import Mapping
from typing import Literal, overload

from wd_discord.models import DiscordModel

from .events import EventName, GuildCreate, Interaction, Message, Ready, VoiceStateUpdate

@overload
def parse_dispatch(name: Literal[EventName.READY], data: Mapping[str, object]) -> Ready: ...
@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_CREATE], data: Mapping[str, object]) -> Message: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_CREATE], data: Mapping[str, object]) -> GuildCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.INTERACTION_CREATE], data: Mapping[str, object]) -> Interaction: ...
@overload
def parse_dispatch(name: Literal[EventName.VOICE_STATE_UPDATE], data: Mapping[str, object]) -> VoiceStateUpdate: ...
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
