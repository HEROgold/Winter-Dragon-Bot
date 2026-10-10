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

from .events import (
    EventName,
    ChannelCreate,
    ChannelDelete,
    ChannelPinsUpdate,
    ChannelUpdate,
    GuildCreate,
    GuildDelete,
    GuildMemberAdd,
    GuildMemberRemove,
    GuildMemberUpdate,
    GuildMembersChunk,
    GuildRoleCreate,
    GuildRoleDelete,
    GuildRoleUpdate,
    GuildUpdate,
    Interaction,
    Message,
    PresenceUpdate,
    Ready,
    ThreadCreate,
    ThreadDelete,
    ThreadListSync,
    ThreadMemberUpdate,
    ThreadMembersUpdate,
    ThreadUpdate,
    UserUpdate,
    VoiceChannelStartTimeUpdate,
    VoiceChannelStatusUpdate,
    VoiceStateUpdate,
)

@overload
def parse_dispatch(name: Literal[EventName.READY], data: Mapping[str, object]) -> Ready: ...
@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_CREATE], data: Mapping[str, object]) -> Message: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_CREATE], data: Mapping[str, object]) -> GuildCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.INTERACTION_CREATE], data: Mapping[str, object]) -> Interaction: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_CREATE], data: Mapping[str, object]) -> ChannelCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_UPDATE], data: Mapping[str, object]) -> ChannelUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_DELETE], data: Mapping[str, object]) -> ChannelDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_PINS_UPDATE], data: Mapping[str, object]) -> ChannelPinsUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_CREATE], data: Mapping[str, object]) -> ThreadCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_UPDATE], data: Mapping[str, object]) -> ThreadUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_DELETE], data: Mapping[str, object]) -> ThreadDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_LIST_SYNC], data: Mapping[str, object]) -> ThreadListSync: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_MEMBER_UPDATE], data: Mapping[str, object]) -> ThreadMemberUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_MEMBERS_UPDATE], data: Mapping[str, object]) -> ThreadMembersUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_UPDATE], data: Mapping[str, object]) -> GuildUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_DELETE], data: Mapping[str, object]) -> GuildDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_MEMBER_ADD], data: Mapping[str, object]) -> GuildMemberAdd: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_MEMBER_REMOVE], data: Mapping[str, object]) -> GuildMemberRemove: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_MEMBER_UPDATE], data: Mapping[str, object]) -> GuildMemberUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_MEMBERS_CHUNK], data: Mapping[str, object]) -> GuildMembersChunk: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_ROLE_CREATE], data: Mapping[str, object]) -> GuildRoleCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_ROLE_UPDATE], data: Mapping[str, object]) -> GuildRoleUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_ROLE_DELETE], data: Mapping[str, object]) -> GuildRoleDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.PRESENCE_UPDATE], data: Mapping[str, object]) -> PresenceUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.USER_UPDATE], data: Mapping[str, object]) -> UserUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.VOICE_CHANNEL_START_TIME_UPDATE], data: Mapping[str, object]
) -> VoiceChannelStartTimeUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.VOICE_CHANNEL_STATUS_UPDATE], data: Mapping[str, object]
) -> VoiceChannelStatusUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.VOICE_STATE_UPDATE], data: Mapping[str, object]) -> VoiceStateUpdate: ...
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
