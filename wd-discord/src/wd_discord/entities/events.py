"""Gateway dispatch events bound to the client that received them.

:mod:`wd_discord.gateway.events` parses each dispatch into a data model; :func:`bind` wraps that model in
the entity a listener acts on, so ``message.channel.send(...)`` needs no client passed around. Events without
an entity yet (anything parsed as :class:`~wd_discord.gateway.events.RawEvent`) come back unchanged.
"""

lazy from dataclasses import dataclass
lazy from functools import cache
lazy from typing import TYPE_CHECKING, Any, cast

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
    ModalSubmitInteraction,
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
    event = EventName.of(model)
    binding = None if event is None else _bindings().get(event)
    if binding is None:
        return model
    if binding.build is None:
        # A binding without a build function names an entity class that takes the client and the model.
        built = cast("Callable[[Client, DiscordModel], ClientBound]", binding.entity)(client, model)
    else:
        built = binding.build(client, model, previous)
    # Each binding builds its own entity, which is one of BoundEvent's members.
    return cast("BoundEvent", built)


@dataclass(frozen=True, slots=True)
class _Binding:
    """What :func:`bind` makes of one event's model."""

    entity: EntityType
    """The entity (or union of entities) a listener receives; ``listener.pyi`` is generated from it."""
    build: Callable[[Client, Any, DiscordModel | None], ClientBound] | None = None
    """Builds the entity from the client, the model and what the event replaced in the cache.

    ``None`` calls :attr:`entity` with the client and the model, which is all most entities need.
    """


@cache
def _bindings() -> Mapping[EventName, _Binding]:
    """Return the entity of each gateway event; the one table adding an event's entity touches."""
    return {
        EventName.READY: _Binding(Ready),
        EventName.MESSAGE_CREATE: _Binding(Message),
        EventName.GUILD_CREATE: _Binding(GatewayGuild),
        EventName.INTERACTION_CREATE: _Binding(AnyInteraction, _interaction),
        EventName.VOICE_STATE_UPDATE: _Binding(VoiceState),
        EventName.GUILD_UPDATE: _Binding(Guild),
        EventName.GUILD_DELETE: _Binding(GuildDelete),
        EventName.CHANNEL_CREATE: _Binding(Channel),
        EventName.CHANNEL_UPDATE: _Binding(Channel),
        EventName.CHANNEL_DELETE: _Binding(Channel),
        EventName.CHANNEL_PINS_UPDATE: _Binding(ChannelPinsUpdate),
        EventName.THREAD_CREATE: _Binding(ThreadCreate),
        EventName.THREAD_UPDATE: _Binding(Channel),
        EventName.THREAD_DELETE: _Binding(ThreadDelete),
        EventName.THREAD_LIST_SYNC: _Binding(ThreadListSync),
        EventName.THREAD_MEMBER_UPDATE: _Binding(ThreadMember, _thread_member),
        EventName.THREAD_MEMBERS_UPDATE: _Binding(ThreadMembersUpdate),
        EventName.VOICE_CHANNEL_STATUS_UPDATE: _Binding(VoiceChannelStatusUpdate),
        EventName.VOICE_CHANNEL_START_TIME_UPDATE: _Binding(VoiceChannelStartTimeUpdate),
        EventName.GUILD_MEMBER_ADD: _Binding(Member, _member),
        EventName.GUILD_MEMBER_REMOVE: _Binding(MemberRemove, _member_remove),
        EventName.GUILD_MEMBERS_CHUNK: _Binding(MembersChunk),
        EventName.GUILD_ROLE_CREATE: _Binding(Role, _role),
        EventName.GUILD_ROLE_UPDATE: _Binding(Role, _role),
        EventName.GUILD_ROLE_DELETE: _Binding(PartialRole, _deleted_role),
        EventName.USER_UPDATE: _Binding(CurrentUser),
        EventName.PRESENCE_UPDATE: _Binding(Presence),
        EventName.MESSAGE_UPDATE: _Binding(Message),
        EventName.MESSAGE_DELETE: _Binding(MessageDelete),
        EventName.MESSAGE_DELETE_BULK: _Binding(MessageDeleteBulk),
        EventName.MESSAGE_REACTION_ADD: _Binding(ReactionAdd),
        EventName.MESSAGE_REACTION_REMOVE: _Binding(ReactionRemove),
        EventName.MESSAGE_REACTION_REMOVE_ALL: _Binding(ReactionRemoveAll),
        EventName.MESSAGE_REACTION_REMOVE_EMOJI: _Binding(ReactionRemoveEmoji),
        EventName.TYPING_START: _Binding(TypingStart),
        EventName.GUILD_EMOJIS_UPDATE: _Binding(GuildEmojisUpdate),
        EventName.GUILD_STICKERS_UPDATE: _Binding(GuildStickersUpdate),
    }


def event_entities() -> Mapping[EventName, EntityType]:
    """Return the entity (or union of entities) :func:`bind` returns for each event; the source of ``listener.pyi``."""
    return {event: binding.entity for event, binding in _bindings().items()}


def _interaction(client: Client, model: wire.Interaction, _previous: DiscordModel | None) -> AnyInteraction:
    """Wrap an interaction in the entity of its type."""
    match model:
        case wire.CommandInteraction():
            return CommandInteraction(client, model)
        case wire.ComponentInteraction():
            return ComponentInteraction(client, model)
        case wire.AutocompleteInteraction():
            return AutocompleteInteraction(client, model)
        case wire.ModalSubmitInteraction():
            return ModalSubmitInteraction(client, model)
        case _:
            return UnknownInteraction(client, model)


def _member(client: Client, model: wire.GuildMemberAdd, _previous: DiscordModel | None) -> Member:
    """Wrap a member who just joined their guild."""
    return Member(client, model, model.guild_id)


def _member_remove(client: Client, model: wire.GuildMemberRemove, previous: DiscordModel | None) -> MemberRemove:
    """Wrap a member's leaving, with their membership as the cache last knew it."""
    return MemberRemove(client, model, previous if isinstance(previous, GuildMember) else None)


def _role(client: Client, model: wire.GuildRoleCreate | wire.GuildRoleUpdate, _previous: DiscordModel | None) -> Role:
    """Wrap the role a role event carries."""
    return Role(client, model.role, model.guild_id)


def _deleted_role(client: Client, model: wire.GuildRoleDelete, _previous: DiscordModel | None) -> PartialRole:
    """Return a handle on a deleted role, which the event names only by ID."""
    return PartialRole(client, model.role_id, model.guild_id)


def _thread_member(client: Client, model: wire.ThreadMemberUpdate, _previous: DiscordModel | None) -> ThreadMember:
    """Wrap the bot's updated membership of a thread; the event always names the thread."""
    return ThreadMember(client, model, model.id)
