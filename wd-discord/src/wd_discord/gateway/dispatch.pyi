# Typed @overload signatures for wd_discord.gateway.dispatch.parse_dispatch.
#
# GENERATED FILE - do not hand-edit. Regenerate with:
#
#     uv run wd-discord/scripts/generate_dispatch_overloads.py
#
# One overload per EventName member that has a model wired up (EventName.X.model is not None) -
# see generate_dispatch_overloads.py for the naming convention and why members without a model
# aren't listed here individually (they already resolve fine through the general fallback below).
# (no module docstring here on purpose - ruff's PYI021 flags docstrings in stub files)

from collections.abc import Mapping
from typing import Literal, overload

from wd_discord.models import DiscordModel

from .events import (
    EventName,
    GuildCreate,
    GuildCreatePayload,
    Interaction,
    InteractionCreatePayload,
    Message,
    MessageCreatePayload,
)

@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_CREATE], data: MessageCreatePayload) -> Message: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_CREATE], data: GuildCreatePayload) -> GuildCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.INTERACTION_CREATE], data: InteractionCreatePayload) -> Interaction: ...
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
