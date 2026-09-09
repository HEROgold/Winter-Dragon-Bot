"""Typed gateway dispatch event payloads and event-name -> model resolution.

Discord's gateway sends DISPATCH frames (op 0) carrying an event name (``t``) and a JSON
payload (``d``). This module maps event names to typed :class:`DiscordModel` payloads (mirroring
the parsing style already used by :func:`~wd_discord.gateway.connection.parse_ready` and
:func:`~wd_discord.gateway.sharding.parse_gateway_bot`) and falls back to :class:`RawEvent` for
anything without a dedicated model, so an unmodeled event never crashes the receive loop.

:class:`EventName` covers every dispatch event Discord currently defines (except READY - see its
own docstring note). Each member carries its own :class:`DiscordModel` subclass as a real
attribute (``EventName.MESSAGE_CREATE.model is Message``) via the "data-carrying enum" pattern (a
custom ``__new__``), so the name and its model live in exactly one place - but only
``MESSAGE_CREATE``/``GUILD_CREATE`` have a real model wired up so far; every other member's
``model`` is ``None`` (dispatches as :class:`RawEvent`) until its payload/model classes get built.

:func:`parse_dispatch` is :func:`~typing.overload`-ed on ``Literal[EventName.X]`` per event so a
literal call site gets its ``data`` argument checked against that event's
:class:`~typing.TypedDict` payload shape and a precisely-typed return value - that's not a
stylistic choice, it's the only construct Python's type checkers have for "the return type is a
function of this runtime value" (the same mechanism typeshed uses for e.g. ``open()``'s
mode-dependent return type; `Annotated` metadata is inert to a checker's control-flow analysis,
so it can't do this). :meth:`Gateway.listen` dispatches on a runtime ``str`` it read off the
socket, not a literal, so it always resolves to the general (non-narrowed) overload.

TODO: most of the overloads below reference a ``<EventName>``/``<EventName>Payload`` pair that
doesn't exist yet (e.g. ``MessageUpdate``/``MessageUpdatePayload`` for MESSAGE_UPDATE) - they're
placeholders for the type-checker-visible shape this module should eventually have, deliberately
left unresolved (real `ty`/ruff errors) rather than silently typed as ``Any``/``DiscordModel``, so
each one is a visible TODO rather than an invisible gap. Build the real TypedDict + DiscordModel
pair for an event, then fix its overload's `data`/return type to reference them for real (see
``MessageCreatePayload``/``Message`` and ``GuildCreatePayload``/``GuildCreate`` for the pattern),
and give the matching :class:`EventName` member a real ``model`` instead of ``None``.

``User``/``Snowflake``/``Mapping`` are imported eagerly (not via ``lazy from``) because pydantic
resolves model field annotations to real classes at class-definition time; a still-unresolved
lazy-import proxy fails schema generation (``PydanticSchemaGenerationError``). ``Guild``/``Channel``
have this same problem internally today (pre-existing, unrelated to this change), so
:class:`GuildCreate` intentionally does not subclass :class:`~wd_discord.guild.Guild` or type its
nested collections as ``list[Channel]`` - see the TODO on :class:`GuildCreate`.
"""

from __future__ import annotations

from collections.abc import Mapping
lazy from enum import StrEnum
lazy from typing import Literal, NotRequired, Self, TypedDict, overload

lazy from pydantic import Field

from wd_discord.models import DiscordModel
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


class RawEvent(DiscordModel):
    """Fallback for any dispatch event without a dedicated model."""

    name: str
    data: Mapping[str, object]


class GuildCreate(DiscordModel):
    """GUILD_CREATE (subset - https://docs.discord.com/developers/events/gateway-events#guild-create).

    TODO(Phase 2): should subclass :class:`~wd_discord.guild.Guild` and type ``channels`` as
    ``list[Channel]``, but ``Guild``/``Channel`` currently fail pydantic schema generation
    themselves (unresolved ``lazy import`` proxies used as nested field types) - fix that
    alongside the Interaction/CommandTree pydantic port, then merge this into ``Guild``.
    """

    id: Snowflake
    name: str
    owner_id: Snowflake
    joined_at: str | None = None
    large: bool | None = None
    unavailable: bool | None = None
    member_count: int | None = None
    channels: list[Mapping[str, object]] = Field(default_factory=list)
    members: list[Mapping[str, object]] = Field(default_factory=list)
    voice_states: list[Mapping[str, object]] = Field(default_factory=list)
    presences: list[Mapping[str, object]] = Field(default_factory=list)


class Message(DiscordModel):
    """MESSAGE_CREATE (subset - https://docs.discord.com/developers/resources/message)."""

    id: Snowflake
    channel_id: Snowflake
    guild_id: Snowflake | None = None
    author: User
    content: str
    timestamp: str
    edited_timestamp: str | None = None
    tts: bool
    mention_everyone: bool
    # TODO(Phase 2): mentions[]/attachments[]/embeds[]/reactions[] need their own models.


class MessageCreatePayload(TypedDict):
    """The raw ``d`` payload of a MESSAGE_CREATE dispatch, as delivered by the gateway (subset).

    Mirrors :class:`Message`'s fields; kept as a separate TypedDict (rather than typing
    :func:`parse_dispatch`'s ``data`` param directly off the pydantic model) so callers get a
    plain-dict shape to construct without needing pydantic, and so the wire shape and the parsed
    model can diverge (e.g. ``author`` here is the raw nested user object, not a ``User``).
    """

    id: str
    channel_id: str
    guild_id: NotRequired[str]
    author: Mapping[str, object]
    content: str
    timestamp: str
    edited_timestamp: NotRequired[str | None]
    tts: bool
    mention_everyone: bool


class GuildCreatePayload(TypedDict):
    """The raw ``d`` payload of a GUILD_CREATE dispatch, as delivered by the gateway (subset)."""

    id: str
    name: str
    owner_id: str
    joined_at: NotRequired[str]
    large: NotRequired[bool]
    unavailable: NotRequired[bool]
    member_count: NotRequired[int]
    channels: NotRequired[list[Mapping[str, object]]]
    members: NotRequired[list[Mapping[str, object]]]
    voice_states: NotRequired[list[Mapping[str, object]]]
    presences: NotRequired[list[Mapping[str, object]]]


class EventName(StrEnum):
    """Every dispatch event name Discord currently defines.

    READY is deliberately not a member here - it's parsed once via
    :func:`~wd_discord.gateway.connection.parse_ready` before the continuous receive loop starts,
    and never appears again on the same connection, so it has no need of a dispatch-time lookup.

    Each member carries its own :class:`DiscordModel` subclass as a real attribute
    (``EventName.MESSAGE_CREATE.model is Message``) via a custom ``__new__``, so the name and its
    model live in exactly one place - but most members' ``model`` is still ``None`` (see the
    module TODO); those dispatch as :class:`RawEvent` until their model gets built.
    """

    model: type[DiscordModel] | None

    def __new__(cls, value: str, model: type[DiscordModel] | None = None) -> Self:
        """Build a member, attaching its ``model`` (if any) alongside the usual str ``value``."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.model = model
        return member

    MESSAGE_CREATE = ("MESSAGE_CREATE", Message)
    GUILD_CREATE = ("GUILD_CREATE", GuildCreate)

    RESUMED = "RESUMED"

    APPLICATION_COMMAND_PERMISSIONS_UPDATE = "APPLICATION_COMMAND_PERMISSIONS_UPDATE"

    AUTO_MODERATION_RULE_CREATE = "AUTO_MODERATION_RULE_CREATE"
    AUTO_MODERATION_RULE_UPDATE = "AUTO_MODERATION_RULE_UPDATE"
    AUTO_MODERATION_RULE_DELETE = "AUTO_MODERATION_RULE_DELETE"
    AUTO_MODERATION_ACTION_EXECUTION = "AUTO_MODERATION_ACTION_EXECUTION"

    CHANNEL_CREATE = "CHANNEL_CREATE"
    CHANNEL_UPDATE = "CHANNEL_UPDATE"
    CHANNEL_DELETE = "CHANNEL_DELETE"
    CHANNEL_PINS_UPDATE = "CHANNEL_PINS_UPDATE"

    THREAD_CREATE = "THREAD_CREATE"
    THREAD_UPDATE = "THREAD_UPDATE"
    THREAD_DELETE = "THREAD_DELETE"
    THREAD_LIST_SYNC = "THREAD_LIST_SYNC"
    THREAD_MEMBER_UPDATE = "THREAD_MEMBER_UPDATE"
    THREAD_MEMBERS_UPDATE = "THREAD_MEMBERS_UPDATE"

    ENTITLEMENT_CREATE = "ENTITLEMENT_CREATE"
    ENTITLEMENT_UPDATE = "ENTITLEMENT_UPDATE"
    ENTITLEMENT_DELETE = "ENTITLEMENT_DELETE"

    GUILD_UPDATE = "GUILD_UPDATE"
    GUILD_DELETE = "GUILD_DELETE"
    GUILD_AUDIT_LOG_ENTRY_CREATE = "GUILD_AUDIT_LOG_ENTRY_CREATE"
    GUILD_BAN_ADD = "GUILD_BAN_ADD"
    GUILD_BAN_REMOVE = "GUILD_BAN_REMOVE"
    GUILD_EMOJIS_UPDATE = "GUILD_EMOJIS_UPDATE"
    GUILD_STICKERS_UPDATE = "GUILD_STICKERS_UPDATE"
    GUILD_INTEGRATIONS_UPDATE = "GUILD_INTEGRATIONS_UPDATE"
    GUILD_MEMBER_ADD = "GUILD_MEMBER_ADD"
    GUILD_MEMBER_REMOVE = "GUILD_MEMBER_REMOVE"
    GUILD_MEMBER_UPDATE = "GUILD_MEMBER_UPDATE"
    GUILD_MEMBERS_CHUNK = "GUILD_MEMBERS_CHUNK"
    GUILD_ROLE_CREATE = "GUILD_ROLE_CREATE"
    GUILD_ROLE_UPDATE = "GUILD_ROLE_UPDATE"
    GUILD_ROLE_DELETE = "GUILD_ROLE_DELETE"
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

    INTERACTION_CREATE = "INTERACTION_CREATE"

    INVITE_CREATE = "INVITE_CREATE"
    INVITE_DELETE = "INVITE_DELETE"

    MESSAGE_UPDATE = "MESSAGE_UPDATE"
    MESSAGE_DELETE = "MESSAGE_DELETE"
    MESSAGE_DELETE_BULK = "MESSAGE_DELETE_BULK"
    MESSAGE_REACTION_ADD = "MESSAGE_REACTION_ADD"
    MESSAGE_REACTION_REMOVE = "MESSAGE_REACTION_REMOVE"
    MESSAGE_REACTION_REMOVE_ALL = "MESSAGE_REACTION_REMOVE_ALL"
    MESSAGE_REACTION_REMOVE_EMOJI = "MESSAGE_REACTION_REMOVE_EMOJI"
    MESSAGE_POLL_VOTE_ADD = "MESSAGE_POLL_VOTE_ADD"
    MESSAGE_POLL_VOTE_REMOVE = "MESSAGE_POLL_VOTE_REMOVE"

    PRESENCE_UPDATE = "PRESENCE_UPDATE"

    STAGE_INSTANCE_CREATE = "STAGE_INSTANCE_CREATE"
    STAGE_INSTANCE_UPDATE = "STAGE_INSTANCE_UPDATE"
    STAGE_INSTANCE_DELETE = "STAGE_INSTANCE_DELETE"

    SUBSCRIPTION_CREATE = "SUBSCRIPTION_CREATE"
    SUBSCRIPTION_UPDATE = "SUBSCRIPTION_UPDATE"
    SUBSCRIPTION_DELETE = "SUBSCRIPTION_DELETE"

    TYPING_START = "TYPING_START"

    USER_UPDATE = "USER_UPDATE"

    VOICE_CHANNEL_EFFECT_SEND = "VOICE_CHANNEL_EFFECT_SEND"
    VOICE_STATE_UPDATE = "VOICE_STATE_UPDATE"
    VOICE_SERVER_UPDATE = "VOICE_SERVER_UPDATE"

    WEBHOOKS_UPDATE = "WEBHOOKS_UPDATE"


# --- parse_dispatch overloads ------------------------------------------------------------
# One per EventName member. MESSAGE_CREATE/GUILD_CREATE reference real types; every other
# overload below references a <EventName>/<EventName>Payload pair that doesn't exist yet - see
# the module TODO. Left unresolved on purpose rather than typed as Any/DiscordModel, so each is
# a visible TODO for `ty`/ruff to point at instead of a silent gap.


@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_CREATE], data: MessageCreatePayload) -> Message: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_CREATE], data: GuildCreatePayload) -> GuildCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.RESUMED], data: ResumedPayload) -> Resumed: ...
@overload
def parse_dispatch(
    name: Literal[EventName.APPLICATION_COMMAND_PERMISSIONS_UPDATE],
    data: ApplicationCommandPermissionsUpdatePayload,
) -> ApplicationCommandPermissionsUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.AUTO_MODERATION_RULE_CREATE],
    data: AutoModerationRuleCreatePayload,
) -> AutoModerationRuleCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.AUTO_MODERATION_RULE_UPDATE],
    data: AutoModerationRuleUpdatePayload,
) -> AutoModerationRuleUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.AUTO_MODERATION_RULE_DELETE],
    data: AutoModerationRuleDeletePayload,
) -> AutoModerationRuleDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.AUTO_MODERATION_ACTION_EXECUTION],
    data: AutoModerationActionExecutionPayload,
) -> AutoModerationActionExecution: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_CREATE], data: ChannelCreatePayload) -> ChannelCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_UPDATE], data: ChannelUpdatePayload) -> ChannelUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.CHANNEL_DELETE], data: ChannelDeletePayload) -> ChannelDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.CHANNEL_PINS_UPDATE],
    data: ChannelPinsUpdatePayload,
) -> ChannelPinsUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_CREATE], data: ThreadCreatePayload) -> ThreadCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_UPDATE], data: ThreadUpdatePayload) -> ThreadUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.THREAD_DELETE], data: ThreadDeletePayload) -> ThreadDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.THREAD_LIST_SYNC],
    data: ThreadListSyncPayload,
) -> ThreadListSync: ...
@overload
def parse_dispatch(
    name: Literal[EventName.THREAD_MEMBER_UPDATE],
    data: ThreadMemberUpdatePayload,
) -> ThreadMemberUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.THREAD_MEMBERS_UPDATE],
    data: ThreadMembersUpdatePayload,
) -> ThreadMembersUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.ENTITLEMENT_CREATE],
    data: EntitlementCreatePayload,
) -> EntitlementCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.ENTITLEMENT_UPDATE],
    data: EntitlementUpdatePayload,
) -> EntitlementUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.ENTITLEMENT_DELETE],
    data: EntitlementDeletePayload,
) -> EntitlementDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_UPDATE], data: GuildUpdatePayload) -> GuildUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_DELETE], data: GuildDeletePayload) -> GuildDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_AUDIT_LOG_ENTRY_CREATE],
    data: GuildAuditLogEntryCreatePayload,
) -> GuildAuditLogEntryCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.GUILD_BAN_ADD], data: GuildBanAddPayload) -> GuildBanAdd: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_BAN_REMOVE],
    data: GuildBanRemovePayload,
) -> GuildBanRemove: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_EMOJIS_UPDATE],
    data: GuildEmojisUpdatePayload,
) -> GuildEmojisUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_STICKERS_UPDATE],
    data: GuildStickersUpdatePayload,
) -> GuildStickersUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_INTEGRATIONS_UPDATE],
    data: GuildIntegrationsUpdatePayload,
) -> GuildIntegrationsUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_MEMBER_ADD],
    data: GuildMemberAddPayload,
) -> GuildMemberAdd: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_MEMBER_REMOVE],
    data: GuildMemberRemovePayload,
) -> GuildMemberRemove: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_MEMBER_UPDATE],
    data: GuildMemberUpdatePayload,
) -> GuildMemberUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_MEMBERS_CHUNK],
    data: GuildMembersChunkPayload,
) -> GuildMembersChunk: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_ROLE_CREATE],
    data: GuildRoleCreatePayload,
) -> GuildRoleCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_ROLE_UPDATE],
    data: GuildRoleUpdatePayload,
) -> GuildRoleUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_ROLE_DELETE],
    data: GuildRoleDeletePayload,
) -> GuildRoleDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SCHEDULED_EVENT_CREATE],
    data: GuildScheduledEventCreatePayload,
) -> GuildScheduledEventCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SCHEDULED_EVENT_UPDATE],
    data: GuildScheduledEventUpdatePayload,
) -> GuildScheduledEventUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SCHEDULED_EVENT_DELETE],
    data: GuildScheduledEventDeletePayload,
) -> GuildScheduledEventDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SCHEDULED_EVENT_USER_ADD],
    data: GuildScheduledEventUserAddPayload,
) -> GuildScheduledEventUserAdd: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SCHEDULED_EVENT_USER_REMOVE],
    data: GuildScheduledEventUserRemovePayload,
) -> GuildScheduledEventUserRemove: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SOUNDBOARD_SOUND_CREATE],
    data: GuildSoundboardSoundCreatePayload,
) -> GuildSoundboardSoundCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SOUNDBOARD_SOUND_UPDATE],
    data: GuildSoundboardSoundUpdatePayload,
) -> GuildSoundboardSoundUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SOUNDBOARD_SOUND_DELETE],
    data: GuildSoundboardSoundDeletePayload,
) -> GuildSoundboardSoundDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.GUILD_SOUNDBOARD_SOUNDS_UPDATE],
    data: GuildSoundboardSoundsUpdatePayload,
) -> GuildSoundboardSoundsUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.SOUNDBOARD_SOUNDS],
    data: SoundboardSoundsPayload,
) -> SoundboardSounds: ...
@overload
def parse_dispatch(
    name: Literal[EventName.INTEGRATION_CREATE],
    data: IntegrationCreatePayload,
) -> IntegrationCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.INTEGRATION_UPDATE],
    data: IntegrationUpdatePayload,
) -> IntegrationUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.INTEGRATION_DELETE],
    data: IntegrationDeletePayload,
) -> IntegrationDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.INTERACTION_CREATE],
    data: InteractionCreatePayload,
) -> InteractionCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.INVITE_CREATE], data: InviteCreatePayload) -> InviteCreate: ...
@overload
def parse_dispatch(name: Literal[EventName.INVITE_DELETE], data: InviteDeletePayload) -> InviteDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_UPDATE], data: MessageUpdatePayload) -> MessageUpdate: ...
@overload
def parse_dispatch(name: Literal[EventName.MESSAGE_DELETE], data: MessageDeletePayload) -> MessageDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_DELETE_BULK],
    data: MessageDeleteBulkPayload,
) -> MessageDeleteBulk: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_REACTION_ADD],
    data: MessageReactionAddPayload,
) -> MessageReactionAdd: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_REACTION_REMOVE],
    data: MessageReactionRemovePayload,
) -> MessageReactionRemove: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_REACTION_REMOVE_ALL],
    data: MessageReactionRemoveAllPayload,
) -> MessageReactionRemoveAll: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_REACTION_REMOVE_EMOJI],
    data: MessageReactionRemoveEmojiPayload,
) -> MessageReactionRemoveEmoji: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_POLL_VOTE_ADD],
    data: MessagePollVoteAddPayload,
) -> MessagePollVoteAdd: ...
@overload
def parse_dispatch(
    name: Literal[EventName.MESSAGE_POLL_VOTE_REMOVE],
    data: MessagePollVoteRemovePayload,
) -> MessagePollVoteRemove: ...
@overload
def parse_dispatch(
    name: Literal[EventName.PRESENCE_UPDATE],
    data: PresenceUpdatePayload,
) -> PresenceUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.STAGE_INSTANCE_CREATE],
    data: StageInstanceCreatePayload,
) -> StageInstanceCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.STAGE_INSTANCE_UPDATE],
    data: StageInstanceUpdatePayload,
) -> StageInstanceUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.STAGE_INSTANCE_DELETE],
    data: StageInstanceDeletePayload,
) -> StageInstanceDelete: ...
@overload
def parse_dispatch(
    name: Literal[EventName.SUBSCRIPTION_CREATE],
    data: SubscriptionCreatePayload,
) -> SubscriptionCreate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.SUBSCRIPTION_UPDATE],
    data: SubscriptionUpdatePayload,
) -> SubscriptionUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.SUBSCRIPTION_DELETE],
    data: SubscriptionDeletePayload,
) -> SubscriptionDelete: ...
@overload
def parse_dispatch(name: Literal[EventName.TYPING_START], data: TypingStartPayload) -> TypingStart: ...
@overload
def parse_dispatch(name: Literal[EventName.USER_UPDATE], data: UserUpdatePayload) -> UserUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.VOICE_CHANNEL_EFFECT_SEND],
    data: VoiceChannelEffectSendPayload,
) -> VoiceChannelEffectSend: ...
@overload
def parse_dispatch(
    name: Literal[EventName.VOICE_STATE_UPDATE],
    data: VoiceStateUpdatePayload,
) -> VoiceStateUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.VOICE_SERVER_UPDATE],
    data: VoiceServerUpdatePayload,
) -> VoiceServerUpdate: ...
@overload
def parse_dispatch(
    name: Literal[EventName.WEBHOOKS_UPDATE],
    data: WebhooksUpdatePayload,
) -> WebhooksUpdate: ...
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel:
    """Parse a dispatch (``t``, ``d``) pair into its typed model, or a :class:`RawEvent` fallback.

    READY is intentionally not handled here - it's parsed once via
    :func:`~wd_discord.gateway.connection.parse_ready` before the continuous receive loop starts,
    and never appears again on the same connection.
    """
    try:
        event = EventName(name)
    except ValueError:
        return RawEvent(name=name, data=data)
    if event.model is None:
        return RawEvent(name=name, data=data)
    return event.model.model_validate(data)
