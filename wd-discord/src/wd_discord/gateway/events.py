"""Typed gateway dispatch event payloads and the DiscordModel each event's name resolves to.

Discord's gateway sends DISPATCH frames (op 0) carrying an event name (``t``) and a JSON
payload (``d``). This module holds the typed :class:`DiscordModel` payloads (mirroring the
parsing style already used by :func:`~wd_discord.gateway.connection.parse_ready` and
:func:`~wd_discord.gateway.sharding.parse_gateway_bot`) plus :class:`EventName`, which resolves
an event name to its model. The actual runtime resolution function,
:func:`~wd_discord.gateway.dispatch.parse_dispatch`, lives in its own module -
:mod:`wd_discord.gateway.dispatch` - paired with a *generated* ``dispatch.pyi`` (see
``wd-discord/scripts/generate_dispatch_overloads.py``) holding its ``@overload`` signatures.
That split exists because a stub file shadows its paired ``.py`` module entirely for type
checkers, so mixing "the real implementation" and "~75 generated overload declarations" in one
file would mean either hand-maintaining the overloads (what the generator exists to avoid) or
letting generated content live next to hand-written runtime logic in the same file.

:class:`EventName` covers every dispatch event Discord currently defines. Each member carries its own
:class:`DiscordModel` subclass as a real attribute (``EventName.MESSAGE_CREATE.model is Message``) via the
"data-carrying enum" pattern (a custom ``__new__``), so the name and its model live in exactly one place. A
member whose ``model`` is still ``None`` dispatches as :class:`RawEvent` until its model gets built (add it here,
attach it to the member, then run the generator).

These are data only; :func:`wd_discord.entities.events.bind` wraps them in the client-bound entities a
listener receives.

``User``/``Snowflake``/``Mapping`` are imported eagerly (not via ``lazy from``) because pydantic
resolves model field annotations to real classes at class-definition time; a still-unresolved
lazy-import proxy fails schema generation (``PydanticSchemaGenerationError``).
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Literal
lazy from enum import StrEnum
lazy from typing import Self, cast

lazy from pydantic import Field, ModelWrapValidatorHandler, model_validator

from wd_discord.authenticate import URL, Token
from wd_discord.components import ComponentType
from wd_discord.embed import Embed
from wd_discord.gateway.presence import Presence
from wd_discord.image import ImageHash
from wd_discord.interactions import ApplicationIntegrationType, InteractionContextType, Locale
from wd_discord.models import DiscordModel
from wd_discord.open_enum import OpenIntEnum
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.permissions import ChannelType, PermissionsField
from wd_discord.resources.channel.channel import Channel
from wd_discord.resources.channel.thread import ThreadMember
from wd_discord.resources.entitlement import Entitlement
from wd_discord.resources.guild.emoji import Emoji
from wd_discord.resources.guild.guild import Guild
from wd_discord.resources.guild.member import GuildMember
from wd_discord.resources.guild.partial_guild import PartialGuild
from wd_discord.resources.guild.role import Role
from wd_discord.resources.guild.sticker import Sticker
from wd_discord.resources.message import Attachment, MentionedUser, Reaction
from wd_discord.resources.user import User
from wd_discord.resources.user.collectibles import Collectibles
from wd_discord.resources.user.profile import Avatar
from wd_discord.resources.voice import VoiceState
from wd_discord.snowflake import Snowflake


class RawEvent(DiscordModel):
    """Fallback for any dispatch event without a dedicated model."""

    name: str
    data: Mapping[str, object]


class UnavailableGuild(DiscordModel):
    """A guild that is offline or not sent yet (https://docs.discord.com/developers/resources/guild#unavailable-guild-object)."""

    id: Snowflake
    unavailable: bool | None = None


class Ready(DiscordModel):
    """READY (https://docs.discord.com/developers/events/gateway-events#ready).

    Parsed by :func:`~wd_discord.gateway.connection.parse_ready`.
    """

    v: int
    user: User
    guilds: list[UnavailableGuild] = Field(default_factory=list[UnavailableGuild])
    """The bot's guilds; each one arrives in full later as a GUILD_CREATE."""
    session_id: str
    resume_gateway_url: URL
    shard: tuple[int, int] | None = None
    application_id: str | None = None


class GuildCreate(Guild):
    """GUILD_CREATE (https://docs.discord.com/developers/events/gateway-events#guild-create).

    A full :class:`~wd_discord.resources.guild.Guild` plus the fields only the gateway sends. ``stage_instances``,
    ``guild_scheduled_events`` and ``soundboard_sounds`` are kept as plain objects until they get models.
    """

    joined_at: str | None = None
    large: bool | None = None
    unavailable: bool | None = None
    member_count: int | None = None
    channels: list[Channel] = Field(default_factory=list[Channel])
    threads: list[Channel] = Field(default_factory=list[Channel])
    members: list[GuildMember] = Field(default_factory=list[GuildMember])
    voice_states: list[VoiceState] = Field(default_factory=list[VoiceState])
    """Who is in which voice channel when the guild arrives; these leave out ``guild_id``."""
    presences: list[Presence] = Field(default_factory=list[Presence])
    """The members' presences; only those of the members sent along."""
    stage_instances: list[dict[str, object]] = Field(default_factory=list[dict[str, object]])
    guild_scheduled_events: list[dict[str, object]] = Field(default_factory=list[dict[str, object]])
    soundboard_sounds: list[dict[str, object]] = Field(default_factory=list[dict[str, object]])

    # Sent by Discord, but not documented.
    lazy: object | None = None
    nsfw: object | None = None
    region: object | None = None
    version: object | None = None
    theme: object | None = None
    profile: object | None = None
    hub_type: object | None = None
    experiments: object | None = None
    home_header: object | None = None
    channel_settings: object | None = None
    premium_features: object | None = None
    activity_instances: object | None = None
    inventory_settings: object | None = None
    embedded_activities: object | None = None
    moderator_reporting: object | None = None
    game_application_ids: object | None = None
    guild_space_settings: object | None = None
    verification_role_id: object | None = None
    official_message_color: object | None = None
    linked_game_organization: object | None = None
    application_command_counts: object | None = None
    latest_onboarding_question_id: object | None = None
    owner_configured_content_level: object | None = None
    premium_progress_bar_enabled_user_updated_at: object | None = None


class VoiceStateUpdate(VoiceState):
    """VOICE_STATE_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-state-update).

    Someone joined, left or moved between voice channels, or changed their mute/deafen state.
    """


class GuildUpdate(Guild):
    """GUILD_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-update): the guild's new state."""


class GuildDelete(UnavailableGuild):
    """GUILD_DELETE (https://docs.discord.com/developers/events/gateway-events#guild-delete).

    The guild went offline when ``unavailable`` is set; without it, the bot left or was removed.
    """


class ChannelCreate(Channel):
    """CHANNEL_CREATE (https://docs.discord.com/developers/events/gateway-events#channel-create): a new guild channel."""


class ChannelUpdate(Channel):
    """CHANNEL_UPDATE (https://docs.discord.com/developers/events/gateway-events#channel-update): the channel's new state."""


class ChannelDelete(Channel):
    """CHANNEL_DELETE (https://docs.discord.com/developers/events/gateway-events#channel-delete): the channel as it was."""


class ChannelPinsUpdate(DiscordModel):
    """CHANNEL_PINS_UPDATE (https://docs.discord.com/developers/events/gateway-events#channel-pins-update).

    A message was pinned or unpinned; not sent when a pinned message is deleted.
    """

    guild_id: Snowflake | None = None
    channel_id: Snowflake
    last_pin_timestamp: datetime | None = None


class ThreadCreate(Channel):
    """THREAD_CREATE (https://docs.discord.com/developers/events/gateway-events#thread-create).

    A thread was created (``newly_created``), or the bot was added to a private thread (``member`` is then set).
    """

    newly_created: bool | None = None


class ThreadUpdate(Channel):
    """THREAD_UPDATE (https://docs.discord.com/developers/events/gateway-events#thread-update): the thread's new state."""


class ThreadDelete(DiscordModel):
    """THREAD_DELETE (https://docs.discord.com/developers/events/gateway-events#thread-delete): which thread is gone."""

    id: Snowflake
    guild_id: Snowflake
    parent_id: Snowflake | None = None
    type: ChannelType


class ThreadListSync(DiscordModel):
    """THREAD_LIST_SYNC (https://docs.discord.com/developers/events/gateway-events#thread-list-sync).

    The bot gained access to channels; these are their active threads. Without ``channel_ids`` the whole guild was
    synced. A listed channel without threads here has none, so any the bot knew of are stale.
    """

    guild_id: Snowflake
    channel_ids: list[Snowflake] | None = None
    threads: list[Channel]
    members: list[ThreadMember]
    """The bot's own membership of each of ``threads`` it has joined."""


class ThreadMemberUpdate(ThreadMember):
    """THREAD_MEMBER_UPDATE (https://docs.discord.com/developers/events/gateway-events#thread-member-update).

    The bot's own membership of a thread changed.
    """

    id: Snowflake  # pyrefly: ignore[bad-override-mutable-attribute] - always sent with this event
    """The thread's ID."""
    guild_id: Snowflake


class AddedThreadMember(ThreadMember):
    """A thread member as THREAD_MEMBERS_UPDATE adds it: with the guild member and their presence."""

    member: GuildMember
    presence: Mapping[str, object] | None = None


class ThreadMembersUpdate(DiscordModel):
    """THREAD_MEMBERS_UPDATE (https://docs.discord.com/developers/events/gateway-events#thread-members-update).

    Members joined or left a thread. Without the GUILD_MEMBERS intent, only the bot's own changes are sent.
    """

    id: Snowflake
    """The thread's ID."""
    guild_id: Snowflake
    member_count: int
    """Roughly how many members the thread has; stops counting at 50."""
    added_members: list[AddedThreadMember] | None = None
    removed_member_ids: list[Snowflake] | None = None


class VoiceChannelStatusUpdate(DiscordModel):
    """VOICE_CHANNEL_STATUS_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-channel-status-update)."""

    id: Snowflake
    """The voice channel's ID."""
    guild_id: Snowflake
    status: str | None
    """The channel's new status; ``None`` once cleared."""


class VoiceChannelStartTimeUpdate(DiscordModel):
    """VOICE_CHANNEL_START_TIME_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-channel-start-time-update)."""

    id: Snowflake
    """The voice channel's ID."""
    guild_id: Snowflake
    voice_start_time: int | None = None
    """When the current voice session in the channel started, as Unix seconds; ``None`` once nobody is in it."""


class GuildMemberAdd(GuildMember):
    """GUILD_MEMBER_ADD (https://docs.discord.com/developers/events/gateway-events#guild-member-add): someone joined."""

    guild_id: Snowflake


class GuildMemberRemove(DiscordModel):
    """GUILD_MEMBER_REMOVE (https://docs.discord.com/developers/events/gateway-events#guild-member-remove).

    Someone left, or was kicked or banned.
    """

    guild_id: Snowflake
    user: User


class GuildMemberUpdate(DiscordModel):
    """GUILD_MEMBER_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-member-update).

    A member's new state, without what Discord leaves out of this event (``deaf``, ``mute`` and ``flags`` may be
    missing), so it isn't a full :class:`~wd_discord.resources.guild.GuildMember`.
    """

    guild_id: Snowflake
    roles: list[Snowflake]
    user: User
    nick: str | None = None
    avatar: ImageHash | None
    banner: ImageHash | None
    joined_at: datetime | None
    premium_since: datetime | None = None
    deaf: bool | None = None
    mute: bool | None = None
    pending: bool | None = None
    communication_disabled_until: datetime | None = None
    avatar_decoration_data: Avatar | None = None
    collectibles: Collectibles | None = None


class GuildMembersChunk(DiscordModel):
    """GUILD_MEMBERS_CHUNK (https://docs.discord.com/developers/events/gateway-events#guild-members-chunk).

    One part of the answer to a Request Guild Members (opcode 8).
    """

    guild_id: Snowflake
    members: list[GuildMember]
    chunk_index: int
    chunk_count: int
    not_found: list[Snowflake] | None = None
    """The requested user IDs that aren't members."""
    presences: list[Presence] | None = None
    nonce: str | None = None


class GuildRoleCreate(DiscordModel):
    """GUILD_ROLE_CREATE (https://docs.discord.com/developers/events/gateway-events#guild-role-create)."""

    guild_id: Snowflake
    role: Role


class GuildRoleUpdate(DiscordModel):
    """GUILD_ROLE_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-role-update)."""

    guild_id: Snowflake
    role: Role


class GuildRoleDelete(DiscordModel):
    """GUILD_ROLE_DELETE (https://docs.discord.com/developers/events/gateway-events#guild-role-delete)."""

    guild_id: Snowflake
    role_id: Snowflake


class UserUpdate(User):
    """USER_UPDATE (https://docs.discord.com/developers/events/gateway-events#user-update): the bot's own user changed."""


class PresenceUpdate(Presence):
    """PRESENCE_UPDATE (https://docs.discord.com/developers/events/gateway-events#presence-update).

    A member's status or activities changed; needs the GUILD_PRESENCES intent.
    """


class InteractionType(OpenIntEnum):
    """The kind of interaction an INTERACTION_CREATE dispatch carries.

    https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object-interaction-type
    """

    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class ResolvedData(DiscordModel):
    """The ``resolved`` block of interaction command data - full objects for referenced IDs.

    ``members`` (partial members, without ``user``, ``deaf`` and ``mute``) and ``messages``/``attachments`` aren't
    modeled yet.
    """

    users: dict[str, User] | None = None
    roles: dict[str, Role] | None = None
    channels: dict[str, Channel] | None = None
    """Partial channels: ``id``, ``name``, ``type``, ``permissions`` and, for threads, ``parent_id``/``thread_metadata``."""


class InteractionDataOption(DiscordModel):
    """One option value as submitted in an interaction (not the command's *definition* - see CommandOption for that)."""

    name: str
    type: int
    value: str | int | float | bool | None = None
    options: list[InteractionDataOption] | None = None
    """The chosen subcommand's own option values (only on SUB_COMMAND / SUB_COMMAND_GROUP options)."""
    focused: bool | None = None


class InteractionData(DiscordModel):
    """The ``data`` block of an application-command INTERACTION_CREATE."""

    id: Snowflake
    name: str
    type: int
    options: list[InteractionDataOption] = Field(default_factory=list[InteractionDataOption])
    resolved: ResolvedData | None = None


class MessageComponentData(DiscordModel):
    """The ``data`` block of a MESSAGE_COMPONENT INTERACTION_CREATE (a button click or select choice)."""

    custom_id: str
    component_type: ComponentType
    id: int | None = None
    """The component's numeric identifier within its message."""
    values: list[str] | None = None
    """The chosen values; only sent for select menus."""


class SubmittedTextInput(DiscordModel):
    """A text input in a modal submit: what the member typed."""

    type: Literal[ComponentType.TEXT_INPUT]
    id: int | None = None
    custom_id: str
    value: str


class SubmittedActionRow(DiscordModel):
    """An action row in a modal submit, holding the components it was built with."""

    type: Literal[ComponentType.ACTION_ROW]
    id: int | None = None
    components: list[SubmittedComponent] = Field(default_factory=list["SubmittedComponent"])


class SubmittedLabel(DiscordModel):
    """A label in a modal submit, holding the one component it labels."""

    type: Literal[ComponentType.LABEL]
    id: int | None = None
    component: SubmittedComponent


class SubmittedOtherComponent(DiscordModel):
    """A submitted component without a text value of its own, such as a select menu; its choices are in ``values``."""

    type: ComponentType
    id: int | None = None
    custom_id: str | None = None
    values: list[str] | None = None


type SubmittedComponent = Annotated[
    SubmittedTextInput | SubmittedActionRow | SubmittedLabel | SubmittedOtherComponent,
    Field(union_mode="left_to_right"),
]
"""A component of a modal submit: the first of these whose ``type`` fits."""


class ModalSubmitData(DiscordModel):
    """The ``data`` block of a MODAL_SUBMIT INTERACTION_CREATE.

    https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object-modal-submit-data
    """

    custom_id: str
    """The ``custom_id`` of the modal."""
    components: list[SubmittedComponent] = Field(default_factory=list["SubmittedComponent"])
    """The submitted components: labels or action rows holding the inputs, each with its ``custom_id`` and ``value``."""


class Message(DiscordModel):
    """MESSAGE_CREATE (subset - https://docs.discord.com/developers/resources/message)."""

    id: Snowflake
    channel_id: Snowflake
    guild_id: Snowflake | None = None
    author: User
    content: str
    timestamp: datetime
    edited_timestamp: datetime | None = None
    tts: bool
    mention_everyone: bool
    mentions: list[MentionedUser] = Field(default_factory=list)
    """Users the message mentions."""
    attachments: list[Attachment] = Field(default_factory=list)
    """Files attached to the message."""
    embeds: list[Embed] = Field(default_factory=list)
    """Embeds in the message."""
    reactions: list[Reaction] = Field(default_factory=list)
    """Reactions to the message; never on MESSAGE_CREATE, only on a fetched message."""


class Interaction(DiscordModel):
    """INTERACTION_CREATE (https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object).

    The fields every interaction shares. Its ``data`` shape depends on ``type``, so each type gets a subclass
    with a precise ``data``: :meth:`model_validate` on this base returns the subclass matching ``type``, so a
    parsed interaction narrows with ``isinstance``. Build a specific interaction through its subclass; calling
    ``Interaction(...)`` directly can't swap in the subclass.
    """

    id: Snowflake
    application_id: Snowflake
    type: InteractionType
    guild_id: Snowflake | None = None
    channel_id: Snowflake | None = None
    member: GuildMember | None = None
    """The invoking member, when invoked in a guild."""
    user: User | None = None
    """The invoking user, when invoked in a DM."""
    token: Token
    """The continuation token for responding to this interaction; valid for 15 minutes."""
    version: int
    app_permissions: PermissionsField | None = None
    """Permissions the app has where the interaction was sent, including overwrites."""
    locale: Locale | None = None
    """The invoking user's selected language; sent on every interaction except PING."""
    guild_locale: Locale | None = None
    """The guild's preferred locale, when invoked in a guild."""
    entitlements: list[Entitlement] | None = None
    """For monetized apps: the invoking user's (and guild's) entitlements."""
    authorizing_integration_owners: dict[ApplicationIntegrationType, Snowflake] | None = None
    """Who installed the app for this interaction, per installation context: a guild ID, a user ID, or ``0``."""
    context: InteractionContextType | None = None
    """Where the interaction was triggered from."""
    attachment_size_limit: int | None = None
    """Attachment size limit in bytes."""
    guild: PartialGuild | None = None
    """The guild the interaction was sent from."""
    channel: Channel | None = None
    """The (partial) channel the interaction was sent from."""

    @model_validator(mode="wrap")
    @classmethod
    def _parse_as_subclass(cls, data: object, handler: ModelWrapValidatorHandler[Interaction]) -> Interaction:
        """Validate a raw interaction on the base class into the subclass its ``type`` names."""
        if cls is not Interaction or not isinstance(data, Mapping):
            return handler(data)
        payload = cast("Mapping[str, object]", data)
        subclass = _INTERACTION_SUBCLASSES.get(payload.get("type"), UnknownInteraction)
        return subclass.model_validate(payload)

    @property
    def invoking_user(self) -> User | None:
        """The user who triggered this interaction, whether invoked in a guild (``member``) or a DM (``user``)."""
        if self.user is not None:
            return self.user
        return self.member.user if self.member is not None else None


class CommandInteraction(Interaction):
    """An APPLICATION_COMMAND interaction: someone ran a command."""

    data: InteractionData


class AutocompleteInteraction(Interaction):
    """An APPLICATION_COMMAND_AUTOCOMPLETE interaction: someone is typing a value for an autocomplete option."""

    data: InteractionData


class ComponentInteraction(Interaction):
    """A MESSAGE_COMPONENT interaction: someone clicked a button or chose from a select menu."""

    data: MessageComponentData
    message: dict[str, object]
    """The message the component is attached to."""


class ModalSubmitInteraction(Interaction):
    """A MODAL_SUBMIT interaction: someone submitted a modal."""

    data: ModalSubmitData
    message: Message | None = None
    """The message the modal was opened from, when it was opened from a component on a message."""


class UnknownInteraction(Interaction):
    """An interaction type without its own subclass yet (PING); ``data`` stays untyped."""

    data: Mapping[str, object] | None = None


_INTERACTION_SUBCLASSES: dict[object, type[Interaction]] = {
    InteractionType.APPLICATION_COMMAND: CommandInteraction,
    InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE: AutocompleteInteraction,
    InteractionType.MESSAGE_COMPONENT: ComponentInteraction,
    InteractionType.MODAL_SUBMIT: ModalSubmitInteraction,
}
"""The subclass each interaction type parses into; IntEnum members hash like the wire ints."""


class MessageUpdate(Message):
    """MESSAGE_UPDATE (https://docs.discord.com/developers/events/gateway-events#message-update): the full edited message."""


class MessageDelete(DiscordModel):
    """MESSAGE_DELETE (https://docs.discord.com/developers/events/gateway-events#message-delete)."""

    id: Snowflake
    channel_id: Snowflake
    guild_id: Snowflake | None = None


class MessageDeleteBulk(DiscordModel):
    """MESSAGE_DELETE_BULK (https://docs.discord.com/developers/events/gateway-events#message-delete-bulk)."""

    ids: list[Snowflake]
    channel_id: Snowflake
    guild_id: Snowflake | None = None


class MessageReactionAdd(DiscordModel):
    """MESSAGE_REACTION_ADD (https://docs.discord.com/developers/events/gateway-events#message-reaction-add)."""

    user_id: Snowflake
    channel_id: Snowflake
    message_id: Snowflake
    guild_id: Snowflake | None = None
    member: GuildMember | None = None
    emoji: PartialEmoji
    message_author_id: Snowflake | None = None
    burst: bool = False
    """Whether this is a super reaction."""
    burst_colors: list[str] = Field(default_factory=list)
    type: int = 0
    """0 for a normal reaction, 1 for a super reaction."""


class MessageReactionRemove(DiscordModel):
    """MESSAGE_REACTION_REMOVE (https://docs.discord.com/developers/events/gateway-events#message-reaction-remove)."""

    user_id: Snowflake
    channel_id: Snowflake
    message_id: Snowflake
    guild_id: Snowflake | None = None
    emoji: PartialEmoji
    burst: bool = False
    type: int = 0


class MessageReactionRemoveAll(DiscordModel):
    """MESSAGE_REACTION_REMOVE_ALL (https://docs.discord.com/developers/events/gateway-events#message-reaction-remove-all)."""

    channel_id: Snowflake
    message_id: Snowflake
    guild_id: Snowflake | None = None


class MessageReactionRemoveEmoji(DiscordModel):
    """MESSAGE_REACTION_REMOVE_EMOJI (https://docs.discord.com/developers/events/gateway-events#message-reaction-remove-emoji)."""

    channel_id: Snowflake
    message_id: Snowflake
    guild_id: Snowflake | None = None
    emoji: PartialEmoji


class TypingStart(DiscordModel):
    """TYPING_START (https://docs.discord.com/developers/events/gateway-events#typing-start)."""

    channel_id: Snowflake
    guild_id: Snowflake | None = None
    user_id: Snowflake
    timestamp: int
    """When the user started typing, in Unix seconds."""
    member: GuildMember | None = None


class GuildEmojisUpdate(DiscordModel):
    """GUILD_EMOJIS_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-emojis-update).

    Carries the guild's full emoji list.
    """

    guild_id: Snowflake
    emojis: list[Emoji]


class GuildStickersUpdate(DiscordModel):
    """GUILD_STICKERS_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-stickers-update).

    Carries the guild's full sticker list.
    """

    guild_id: Snowflake
    stickers: list[Sticker]


class EventName(StrEnum):
    """Every dispatch event name Discord currently defines.

    READY arrives once per connection. :meth:`~wd_discord.gateway.connection.Gateway.connect` parses it with
    :func:`~wd_discord.gateway.connection.parse_ready` (never :func:`~wd_discord.gateway.dispatch.parse_dispatch`),
    and :meth:`~wd_discord.gateway.connection.Gateway.listen` then hands it to listeners like any other event.

    Each member carries its own :class:`DiscordModel` subclass as a real attribute
    (``EventName.MESSAGE_CREATE.model is Message``) via a custom ``__new__``, so the name and its
    model live in exactly one place - but most members' ``model`` is still ``None``; those
    dispatch as :class:`RawEvent` until their model gets built (see the module docstring).

    https://docs.discord.com/developers/events/gateway-events#receive-events
    """

    model: type[DiscordModel] | None

    def __new__(cls, value: str, model: type[DiscordModel] | None = None) -> Self:
        """Build a member, attaching its ``model`` (if any) alongside the usual str ``value``."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.model = model
        return member

    READY = ("READY", Ready)
    MESSAGE_CREATE = ("MESSAGE_CREATE", Message)
    GUILD_CREATE = ("GUILD_CREATE", GuildCreate)
    INTERACTION_CREATE = ("INTERACTION_CREATE", Interaction)

    RESUMED = "RESUMED"

    APPLICATION_COMMAND_PERMISSIONS_UPDATE = "APPLICATION_COMMAND_PERMISSIONS_UPDATE"

    AUTO_MODERATION_RULE_CREATE = "AUTO_MODERATION_RULE_CREATE"
    AUTO_MODERATION_RULE_UPDATE = "AUTO_MODERATION_RULE_UPDATE"
    AUTO_MODERATION_RULE_DELETE = "AUTO_MODERATION_RULE_DELETE"
    AUTO_MODERATION_ACTION_EXECUTION = "AUTO_MODERATION_ACTION_EXECUTION"

    CHANNEL_CREATE = ("CHANNEL_CREATE", ChannelCreate)
    CHANNEL_UPDATE = ("CHANNEL_UPDATE", ChannelUpdate)
    CHANNEL_DELETE = ("CHANNEL_DELETE", ChannelDelete)
    CHANNEL_PINS_UPDATE = ("CHANNEL_PINS_UPDATE", ChannelPinsUpdate)

    THREAD_CREATE = ("THREAD_CREATE", ThreadCreate)
    THREAD_UPDATE = ("THREAD_UPDATE", ThreadUpdate)
    THREAD_DELETE = ("THREAD_DELETE", ThreadDelete)
    THREAD_LIST_SYNC = ("THREAD_LIST_SYNC", ThreadListSync)
    THREAD_MEMBER_UPDATE = ("THREAD_MEMBER_UPDATE", ThreadMemberUpdate)
    THREAD_MEMBERS_UPDATE = ("THREAD_MEMBERS_UPDATE", ThreadMembersUpdate)

    ENTITLEMENT_CREATE = "ENTITLEMENT_CREATE"
    ENTITLEMENT_UPDATE = "ENTITLEMENT_UPDATE"
    ENTITLEMENT_DELETE = "ENTITLEMENT_DELETE"

    GUILD_UPDATE = ("GUILD_UPDATE", GuildUpdate)
    GUILD_DELETE = ("GUILD_DELETE", GuildDelete)
    GUILD_AUDIT_LOG_ENTRY_CREATE = "GUILD_AUDIT_LOG_ENTRY_CREATE"
    GUILD_BAN_ADD = "GUILD_BAN_ADD"
    GUILD_BAN_REMOVE = "GUILD_BAN_REMOVE"
    GUILD_EMOJIS_UPDATE = ("GUILD_EMOJIS_UPDATE", GuildEmojisUpdate)
    GUILD_STICKERS_UPDATE = ("GUILD_STICKERS_UPDATE", GuildStickersUpdate)
    GUILD_INTEGRATIONS_UPDATE = "GUILD_INTEGRATIONS_UPDATE"
    GUILD_MEMBER_ADD = ("GUILD_MEMBER_ADD", GuildMemberAdd)
    GUILD_MEMBER_REMOVE = ("GUILD_MEMBER_REMOVE", GuildMemberRemove)
    GUILD_MEMBER_UPDATE = ("GUILD_MEMBER_UPDATE", GuildMemberUpdate)
    GUILD_MEMBERS_CHUNK = ("GUILD_MEMBERS_CHUNK", GuildMembersChunk)
    GUILD_ROLE_CREATE = ("GUILD_ROLE_CREATE", GuildRoleCreate)
    GUILD_ROLE_UPDATE = ("GUILD_ROLE_UPDATE", GuildRoleUpdate)
    GUILD_ROLE_DELETE = ("GUILD_ROLE_DELETE", GuildRoleDelete)
    GUILD_SCHEDULED_EVENT_CREATE = "GUILD_SCHEDULED_EVENT_CREATE"
    GUILD_SCHEDULED_EVENT_UPDATE = "GUILD_SCHEDULED_EVENT_UPDATE"
    GUILD_SCHEDULED_EVENT_DELETE = "GUILD_SCHEDULED_EVENT_DELETE"
    GUILD_SCHEDULED_EVENT_USER_ADD = "GUILD_SCHEDULED_EVENT_USER_ADD"
    GUILD_SCHEDULED_EVENT_USER_REMOVE = "GUILD_SCHEDULED_EVENT_USER_REMOVE"
    GUILD_SOUNDBOARD_SOUND_CREATE = "GUILD_SOUNDBOARD_SOUND_CREATE"
    GUILD_SOUNDBOARD_SOUND_UPDATE = "GUILD_SOUNDBOARD_SOUND_UPDATE"
    GUILD_SOUNDBOARD_SOUND_DELETE = "GUILD_SOUNDBOARD_SOUND_DELETE"
    GUILD_SOUNDBOARD_SOUNDS_UPDATE = "GUILD_SOUNDBOARD_SOUNDS_UPDATE"

    SOUNDBOARD_SOUNDS = "SOUNDBOARD_SOUNDS"

    INTEGRATION_CREATE = "INTEGRATION_CREATE"
    INTEGRATION_UPDATE = "INTEGRATION_UPDATE"
    INTEGRATION_DELETE = "INTEGRATION_DELETE"

    INVITE_CREATE = "INVITE_CREATE"
    INVITE_DELETE = "INVITE_DELETE"

    MESSAGE_UPDATE = ("MESSAGE_UPDATE", MessageUpdate)
    MESSAGE_DELETE = ("MESSAGE_DELETE", MessageDelete)
    MESSAGE_DELETE_BULK = ("MESSAGE_DELETE_BULK", MessageDeleteBulk)
    MESSAGE_REACTION_ADD = ("MESSAGE_REACTION_ADD", MessageReactionAdd)
    MESSAGE_REACTION_REMOVE = ("MESSAGE_REACTION_REMOVE", MessageReactionRemove)
    MESSAGE_REACTION_REMOVE_ALL = ("MESSAGE_REACTION_REMOVE_ALL", MessageReactionRemoveAll)
    MESSAGE_REACTION_REMOVE_EMOJI = ("MESSAGE_REACTION_REMOVE_EMOJI", MessageReactionRemoveEmoji)
    MESSAGE_POLL_VOTE_ADD = "MESSAGE_POLL_VOTE_ADD"
    MESSAGE_POLL_VOTE_REMOVE = "MESSAGE_POLL_VOTE_REMOVE"

    PRESENCE_UPDATE = ("PRESENCE_UPDATE", PresenceUpdate)

    STAGE_INSTANCE_CREATE = "STAGE_INSTANCE_CREATE"
    STAGE_INSTANCE_UPDATE = "STAGE_INSTANCE_UPDATE"
    STAGE_INSTANCE_DELETE = "STAGE_INSTANCE_DELETE"

    SUBSCRIPTION_CREATE = "SUBSCRIPTION_CREATE"
    SUBSCRIPTION_UPDATE = "SUBSCRIPTION_UPDATE"
    SUBSCRIPTION_DELETE = "SUBSCRIPTION_DELETE"

    TYPING_START = ("TYPING_START", TypingStart)

    USER_UPDATE = ("USER_UPDATE", UserUpdate)

    VOICE_CHANNEL_EFFECT_SEND = "VOICE_CHANNEL_EFFECT_SEND"
    VOICE_CHANNEL_START_TIME_UPDATE = ("VOICE_CHANNEL_START_TIME_UPDATE", VoiceChannelStartTimeUpdate)
    VOICE_CHANNEL_STATUS_UPDATE = ("VOICE_CHANNEL_STATUS_UPDATE", VoiceChannelStatusUpdate)
    VOICE_STATE_UPDATE = ("VOICE_STATE_UPDATE", VoiceStateUpdate)
    VOICE_SERVER_UPDATE = "VOICE_SERVER_UPDATE"

    WEBHOOKS_UPDATE = "WEBHOOKS_UPDATE"
