"""Gateway dispatch events bound to the client that received them.

:mod:`wd_discord.gateway.events` parses each dispatch into a data model; :func:`bind` wraps that model in
the entity a listener acts on, so ``message.channel.send(...)`` needs no client passed around. Events without
an entity yet (anything parsed as :class:`~wd_discord.gateway.events.RawEvent`) come back unchanged.
"""

lazy from functools import cache
lazy from typing import TYPE_CHECKING, cast

lazy from wd_discord.entities.channel import Channel, ThreadMember
lazy from wd_discord.entities.dispatches import (
    ChannelPinsUpdate,
    GuildDelete,
    GuildEmojisUpdate,
    GuildStickersUpdate,
    MemberRemove,
    MembersChunk,
    MessageDelete,
    MessageDeleteBulk,
    ReactionAdd,
    ReactionRemove,
    ReactionRemoveAll,
    ReactionRemoveEmoji,
    ThreadCreate,
    ThreadDelete,
    ThreadListSync,
    ThreadMembersUpdate,
    TypingStart,
    VoiceChannelStartTimeUpdate,
    VoiceChannelStatusUpdate,
)
lazy from wd_discord.entities.guild import GatewayGuild, Guild
lazy from wd_discord.entities.interaction import (
    AnyInteraction,
    AutocompleteInteraction,
    CommandInteraction,
    ComponentInteraction,
    UnknownInteraction,
)
lazy from wd_discord.entities.member import Member
lazy from wd_discord.entities.message import Message
lazy from wd_discord.entities.presence import Presence
lazy from wd_discord.entities.ready import Ready
lazy from wd_discord.entities.role import PartialRole, Role
lazy from wd_discord.entities.user import CurrentUser
lazy from wd_discord.entities.voice import VoiceState
lazy from wd_discord.gateway import events as wire
lazy from wd_discord.gateway.events import EventName
lazy from wd_discord.resources.guild import GuildMember


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from wd_discord.client import Client
    from wd_discord.entities.base import ClientBound, EntityType
    from wd_discord.models import DiscordModel


type BoundEvent = (
    AnyInteraction
    | Message
    | GatewayGuild
    | Guild
    | Channel
    | ThreadMember
    | Ready
    | VoiceState
    | GuildDelete
    | ChannelPinsUpdate
    | ThreadCreate
    | ThreadDelete
    | ThreadListSync
    | ThreadMembersUpdate
    | VoiceChannelStatusUpdate
    | VoiceChannelStartTimeUpdate
    | Member
    | MemberRemove
    | MembersChunk
    | Role
    | PartialRole
    | CurrentUser
    | Presence
    | GuildEmojisUpdate
    | GuildStickersUpdate
    | MessageDelete
    | MessageDeleteBulk
    | ReactionAdd
    | ReactionRemove
    | ReactionRemoveAll
    | ReactionRemoveEmoji
    | TypingStart
)
"""Every entity :func:`bind` can return; ``match`` on it to handle each event."""


def bind(client: Client, model: DiscordModel, previous: DiscordModel | None = None) -> BoundEvent | DiscordModel:
    """Wrap a parsed dispatch ``model`` in the entity bound to ``client``, or return it as is if it has none.

    ``previous`` is what the event replaced in the client's cache. Only GUILD_MEMBER_REMOVE uses it: the member
    is gone from the cache once it's applied, and the event names only the user.
    """
    if isinstance(model, wire.GuildMemberRemove):
        return MemberRemove(client, model, previous if isinstance(previous, GuildMember) else None)
    binder = _binders().get(type(model))
    # The table pairs each model with its own entity, which is one of BoundEvent's members.
    return model if binder is None else cast("BoundEvent", binder(client, model))


@cache
def _binders() -> Mapping[type[DiscordModel], Callable[..., ClientBound]]:
    """Return what builds the entity of each dispatch model, keyed by the model's exact class.

    An entity that needs more than the client and the model gets a function here instead of its class.
    """
    return {
        wire.Ready: Ready,
        wire.Message: Message,
        wire.GuildCreate: GatewayGuild,
        wire.CommandInteraction: CommandInteraction,
        wire.ComponentInteraction: ComponentInteraction,
        wire.AutocompleteInteraction: AutocompleteInteraction,
        wire.UnknownInteraction: UnknownInteraction,
        wire.VoiceStateUpdate: VoiceState,
        wire.GuildUpdate: Guild,
        wire.GuildDelete: GuildDelete,
        wire.ChannelCreate: Channel,
        wire.ChannelUpdate: Channel,
        wire.ChannelDelete: Channel,
        wire.ChannelPinsUpdate: ChannelPinsUpdate,
        wire.ThreadCreate: ThreadCreate,
        wire.ThreadUpdate: Channel,
        wire.ThreadDelete: ThreadDelete,
        wire.ThreadListSync: ThreadListSync,
        wire.ThreadMemberUpdate: _thread_member,
        wire.ThreadMembersUpdate: ThreadMembersUpdate,
        wire.VoiceChannelStatusUpdate: VoiceChannelStatusUpdate,
        wire.VoiceChannelStartTimeUpdate: VoiceChannelStartTimeUpdate,
        wire.GuildMemberAdd: _member,
        wire.GuildMembersChunk: MembersChunk,
        wire.GuildRoleCreate: _role,
        wire.GuildRoleUpdate: _role,
        wire.GuildRoleDelete: _deleted_role,
        wire.UserUpdate: CurrentUser,
        wire.PresenceUpdate: Presence,
        wire.MessageUpdate: Message,
        wire.MessageDelete: MessageDelete,
        wire.MessageDeleteBulk: MessageDeleteBulk,
        wire.MessageReactionAdd: ReactionAdd,
        wire.MessageReactionRemove: ReactionRemove,
        wire.MessageReactionRemoveAll: ReactionRemoveAll,
        wire.MessageReactionRemoveEmoji: ReactionRemoveEmoji,
        wire.TypingStart: TypingStart,
        wire.GuildEmojisUpdate: GuildEmojisUpdate,
        wire.GuildStickersUpdate: GuildStickersUpdate,
    }


def _member(client: Client, model: wire.GuildMemberAdd) -> Member:
    """Wrap a member who just joined their guild."""
    return Member(client, model, model.guild_id)


def _role(client: Client, model: wire.GuildRoleCreate | wire.GuildRoleUpdate) -> Role:
    """Wrap the role a role event carries."""
    return Role(client, model.role, model.guild_id)


def _deleted_role(client: Client, model: wire.GuildRoleDelete) -> PartialRole:
    """Return a handle on a deleted role, which the event names only by ID."""
    return PartialRole(client, model.role_id, model.guild_id)


def _thread_member(client: Client, model: wire.ThreadMemberUpdate) -> ThreadMember:
    """Wrap the bot's updated membership of a thread; the event always names the thread."""
    return ThreadMember(client, model, model.id)


def event_entities() -> Mapping[EventName, EntityType]:
    """Return the entity (or union of entities) :func:`bind` returns for each event; the source of ``listener.pyi``."""
    return {
        EventName.READY: Ready,
        EventName.MESSAGE_CREATE: Message,
        EventName.GUILD_CREATE: GatewayGuild,
        EventName.INTERACTION_CREATE: AnyInteraction,
        EventName.VOICE_STATE_UPDATE: VoiceState,
        EventName.GUILD_UPDATE: Guild,
        EventName.GUILD_DELETE: GuildDelete,
        EventName.CHANNEL_CREATE: Channel,
        EventName.CHANNEL_UPDATE: Channel,
        EventName.CHANNEL_DELETE: Channel,
        EventName.CHANNEL_PINS_UPDATE: ChannelPinsUpdate,
        EventName.THREAD_CREATE: ThreadCreate,
        EventName.THREAD_UPDATE: Channel,
        EventName.THREAD_DELETE: ThreadDelete,
        EventName.THREAD_LIST_SYNC: ThreadListSync,
        EventName.THREAD_MEMBER_UPDATE: ThreadMember,
        EventName.THREAD_MEMBERS_UPDATE: ThreadMembersUpdate,
        EventName.VOICE_CHANNEL_STATUS_UPDATE: VoiceChannelStatusUpdate,
        EventName.VOICE_CHANNEL_START_TIME_UPDATE: VoiceChannelStartTimeUpdate,
        EventName.GUILD_MEMBER_ADD: Member,
        EventName.GUILD_MEMBER_REMOVE: MemberRemove,
        EventName.GUILD_MEMBERS_CHUNK: MembersChunk,
        EventName.GUILD_ROLE_CREATE: Role,
        EventName.GUILD_ROLE_UPDATE: Role,
        EventName.GUILD_ROLE_DELETE: PartialRole,
        EventName.USER_UPDATE: CurrentUser,
        EventName.PRESENCE_UPDATE: Presence,
        EventName.MESSAGE_UPDATE: Message,
        EventName.MESSAGE_DELETE: MessageDelete,
        EventName.MESSAGE_DELETE_BULK: MessageDeleteBulk,
        EventName.MESSAGE_REACTION_ADD: ReactionAdd,
        EventName.MESSAGE_REACTION_REMOVE: ReactionRemove,
        EventName.MESSAGE_REACTION_REMOVE_ALL: ReactionRemoveAll,
        EventName.MESSAGE_REACTION_REMOVE_EMOJI: ReactionRemoveEmoji,
        EventName.TYPING_START: TypingStart,
        EventName.GUILD_EMOJIS_UPDATE: GuildEmojisUpdate,
        EventName.GUILD_STICKERS_UPDATE: GuildStickersUpdate,
    }
