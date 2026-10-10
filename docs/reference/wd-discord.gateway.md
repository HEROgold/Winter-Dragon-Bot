<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.gateway` (wd-discord)
Discord gateway (WebSocket) support: connection, payload helpers, and sharding.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.gateway` — `wd-discord/src/wd_discord/gateway/__init__.py`

- exports: DEFAULT_GATEWAY_URL, EventName, Gateway, GatewayActivity, GatewayBotInfo, GuildCreate, Message, Opcode,
  RawEvent, Ready, SessionStartLimit, ShardManager, Status, UnavailableGuild, build_identify, build_presence,
  fetch_gateway_bot, identify_batches, parse_dispatch, parse_gateway_bot, parse_ready, rate_limit_key,
  shard_id_for_guild

## `wd_discord.gateway.connection` — `wd-discord/src/wd_discord/gateway/connection.py`
A minimal Discord Gateway (WebSocket) connection for wd-discord.

- module names: DEFAULT_GATEWAY_URL
- `type GatewayFrame = _DispatchFrame | _HeartbeatRequestFrame | _ReconnectFrame | _InvalidSessionFrame | _HeartbeatAckFrame`
- `build_presence(activities: list[GatewayActivity], status: Status | str=Status.online, *, afk: bool=False, since: int | None=None) -> dict[str, Any]` — Build the ``d`` payload for a Presence Update (object -> API).
- `build_identify(token: str, intents: Intents, *, shard: tuple[int, int] | None=None, presence: dict[str, Any] | None=None) -> dict[str, Any]` — Build the ``d`` payload for an IDENTIFY (object -> API).
- `parse_ready(payload: dict[str, Any]) -> Ready` — Parse a READY dispatch payload into a :class:`Ready` (API -> object).

### `class Opcode(IntEnum)`
Discord gateway opcodes (the subset this client uses).

- attributes: DISPATCH, HEARTBEAT, IDENTIFY, PRESENCE_UPDATE, RESUME, RECONNECT, REQUEST_GUILD_MEMBERS, INVALID_SESSION,
  HELLO, HEARTBEAT_ACK

### `@dataclass class GatewayActivity`
An activity shown on the bot's presence (object -> API via :meth:`to_dict`).

- fields: name: str, type: Activity, url: str | None, state: str | None
- `to_dict() -> dict[str, Any]` — Serialize to the Discord activity object.

### `class Gateway(LoggerMixin)`
A minimal async Discord gateway client.

- `async connect(*, presence: dict[str, Any] | None=None) -> Ready` — Open the connection, identify, and return once READY is received.
- `async listen(dispatch: Callable[[str, DiscordModel], Awaitable[None]]) -> None` — Receive gateway frames forever, updating ``_seq`` and invoking ``dispatch`` on DISPATCH.
- `async update_presence(activities: list[GatewayActivity], status: Status | str=Status.online) -> None` — Send a Presence Update (op 3) to set the bot's activity/status.
- `async close() -> None` — Cancel the heartbeat and close the WebSocket.

## `wd_discord.gateway.dispatch` — `wd-discord/src/wd_discord/gateway/dispatch.py`
Runtime resolution of a gateway dispatch (event name, payload) pair into a typed model.

- `parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel` — Parse a dispatch (``t``, ``d``) pair into its typed model, or a RawEvent fallback.

## `wd_discord.gateway.events` — `wd-discord/src/wd_discord/gateway/events.py`
Typed gateway dispatch event payloads and the DiscordModel each event's name resolves to.

### `class RawEvent(DiscordModel)`
Fallback for any dispatch event without a dedicated model.

- fields: name: str, data: Mapping[str, object]

### `class UnavailableGuild(DiscordModel)`
A guild that is offline or not sent yet (https://docs.discord.com/developers/resources/guild#unavailable-guild-object).

- fields: id: Snowflake, unavailable: bool | None

### `class Ready(DiscordModel)`
READY (https://docs.discord.com/developers/events/gateway-events#ready).

- fields: v: int, user: User, guilds: list[UnavailableGuild], session_id: str, resume_gateway_url: str, shard:
  tuple[int, int] | None, application_id: str | None

### `class GuildCreate(Guild)`
GUILD_CREATE (https://docs.discord.com/developers/events/gateway-events#guild-create).

- fields: joined_at: str | None, large: bool | None, unavailable: bool | None, member_count: int | None, channels:
  list[Channel], threads: list[Channel], members: list[GuildMember], voice_states: list[VoiceState], presences:
  list[Presence]

### `class VoiceStateUpdate(VoiceState)`
VOICE_STATE_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-state-update).

### `class GuildUpdate(Guild)`
GUILD_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-update): the guild's new state.

### `class GuildDelete(UnavailableGuild)`
GUILD_DELETE (https://docs.discord.com/developers/events/gateway-events#guild-delete).

### `class ChannelCreate(Channel)`
CHANNEL_CREATE (https://docs.discord.com/developers/events/gateway-events#channel-create): a new guild channel.

### `class ChannelUpdate(Channel)`
CHANNEL_UPDATE (https://docs.discord.com/developers/events/gateway-events#channel-update): the channel's new state.

### `class ChannelDelete(Channel)`
CHANNEL_DELETE (https://docs.discord.com/developers/events/gateway-events#channel-delete): the channel as it was.

### `class ChannelPinsUpdate(DiscordModel)`
CHANNEL_PINS_UPDATE (https://docs.discord.com/developers/events/gateway-events#channel-pins-update).

- fields: guild_id: Snowflake | None, channel_id: Snowflake, last_pin_timestamp: datetime | None

### `class ThreadCreate(Channel)`
THREAD_CREATE (https://docs.discord.com/developers/events/gateway-events#thread-create).

- fields: newly_created: bool | None

### `class ThreadUpdate(Channel)`
THREAD_UPDATE (https://docs.discord.com/developers/events/gateway-events#thread-update): the thread's new state.

### `class ThreadDelete(DiscordModel)`
THREAD_DELETE (https://docs.discord.com/developers/events/gateway-events#thread-delete): which thread is gone.

- fields: id: Snowflake, guild_id: Snowflake, parent_id: Snowflake | None, type: ChannelType

### `class ThreadListSync(DiscordModel)`
THREAD_LIST_SYNC (https://docs.discord.com/developers/events/gateway-events#thread-list-sync).

- fields: guild_id: Snowflake, channel_ids: list[Snowflake] | None, threads: list[Channel], members: list[ThreadMember]

### `class ThreadMemberUpdate(ThreadMember)`
THREAD_MEMBER_UPDATE (https://docs.discord.com/developers/events/gateway-events#thread-member-update).

- fields: id: Snowflake, guild_id: Snowflake

### `class AddedThreadMember(ThreadMember)`
A thread member as THREAD_MEMBERS_UPDATE adds it: with the guild member and their presence.

- fields: member: GuildMember, presence: Mapping[str, object] | None

### `class ThreadMembersUpdate(DiscordModel)`
THREAD_MEMBERS_UPDATE (https://docs.discord.com/developers/events/gateway-events#thread-members-update).

- fields: id: Snowflake, guild_id: Snowflake, member_count: int, added_members: list[AddedThreadMember] | None,
  removed_member_ids: list[Snowflake] | None

### `class VoiceChannelStatusUpdate(DiscordModel)`
VOICE_CHANNEL_STATUS_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-channel-status-update).

- fields: id: Snowflake, guild_id: Snowflake, status: str | None

### `class VoiceChannelStartTimeUpdate(DiscordModel)`
VOICE_CHANNEL_START_TIME_UPDATE (https://docs.discord.com/developers/events/gateway-events#voice-channel-start-time-update).

- fields: id: Snowflake, guild_id: Snowflake, voice_start_time: int | None

### `class GuildMemberAdd(GuildMember)`
GUILD_MEMBER_ADD (https://docs.discord.com/developers/events/gateway-events#guild-member-add): someone joined.

- fields: guild_id: Snowflake

### `class GuildMemberRemove(DiscordModel)`
GUILD_MEMBER_REMOVE (https://docs.discord.com/developers/events/gateway-events#guild-member-remove).

- fields: guild_id: Snowflake, user: User

### `class GuildMemberUpdate(DiscordModel)`
GUILD_MEMBER_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-member-update).

- fields: guild_id: Snowflake, roles: list[Snowflake], user: User, nick: str | None, avatar: ImageHash | None, banner:
  ImageHash | None, joined_at: datetime | None, premium_since: datetime | None, deaf: bool | None, mute: bool | None,
  pending: bool | None, communication_disabled_until: datetime | None, avatar_decoration_data: Avatar | None,
  collectibles: Collectibles | None

### `class GuildMembersChunk(DiscordModel)`
GUILD_MEMBERS_CHUNK (https://docs.discord.com/developers/events/gateway-events#guild-members-chunk).

- fields: guild_id: Snowflake, members: list[GuildMember], chunk_index: int, chunk_count: int, not_found:
  list[Snowflake] | None, presences: list[Presence] | None, nonce: str | None

### `class GuildRoleCreate(DiscordModel)`
GUILD_ROLE_CREATE (https://docs.discord.com/developers/events/gateway-events#guild-role-create).

- fields: guild_id: Snowflake, role: Role

### `class GuildRoleUpdate(DiscordModel)`
GUILD_ROLE_UPDATE (https://docs.discord.com/developers/events/gateway-events#guild-role-update).

- fields: guild_id: Snowflake, role: Role

### `class GuildRoleDelete(DiscordModel)`
GUILD_ROLE_DELETE (https://docs.discord.com/developers/events/gateway-events#guild-role-delete).

- fields: guild_id: Snowflake, role_id: Snowflake

### `class UserUpdate(User)`
USER_UPDATE (https://docs.discord.com/developers/events/gateway-events#user-update): the bot's own user changed.

### `class PresenceUpdate(Presence)`
PRESENCE_UPDATE (https://docs.discord.com/developers/events/gateway-events#presence-update).

### `class InteractionType(IntEnum)`
The kind of interaction an INTERACTION_CREATE dispatch carries.

- attributes: PING, APPLICATION_COMMAND, MESSAGE_COMPONENT, APPLICATION_COMMAND_AUTOCOMPLETE, MODAL_SUBMIT

### `class ResolvedData(DiscordModel)`
The ``resolved`` block of interaction command data - full objects for referenced IDs.

- fields: users: dict[str, User] | None, roles: dict[str, Role] | None, channels: dict[str, Channel] | None

### `class InteractionDataOption(DiscordModel)`
One option value as submitted in an interaction (not the command's *definition* - see CommandOption for that).

- fields: name: str, type: int, value: str | int | float | bool | None, options: list[InteractionDataOption] | None,
  focused: bool | None

### `class InteractionData(DiscordModel)`
The ``data`` block of an application-command INTERACTION_CREATE.

- fields: id: Snowflake, name: str, type: int, options: list[InteractionDataOption], resolved: ResolvedData | None

### `class MessageComponentData(DiscordModel)`
The ``data`` block of a MESSAGE_COMPONENT INTERACTION_CREATE (a button click or select choice).

- fields: custom_id: str, component_type: ComponentType, id: int | None, values: list[str] | None

### `class Interaction(DiscordModel)`
INTERACTION_CREATE (https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object).

- fields: id: Snowflake, application_id: Snowflake, type: InteractionType, guild_id: Snowflake | None, channel_id:
  Snowflake | None, member: GuildMember | None, user: User | None, token: str, version: int, app_permissions:
  PermissionsField | None, locale: Locale | None, guild_locale: Locale | None, entitlements: list[Entitlement] | None,
  authorizing_integration_owners: dict[ApplicationIntegrationType, Snowflake] | None, context: InteractionContextType |
  None, attachment_size_limit: int | None, guild: PartialGuild | None, channel: Channel | None
- `@property invoking_user -> User | None` — The user who triggered this interaction, whether invoked in a guild (``member``) or a DM (``user``).

### `class CommandInteraction(Interaction)`
An APPLICATION_COMMAND interaction: someone ran a command.

- fields: data: InteractionData

### `class AutocompleteInteraction(Interaction)`
An APPLICATION_COMMAND_AUTOCOMPLETE interaction: someone is typing a value for an autocomplete option.

- fields: data: InteractionData

### `class ComponentInteraction(Interaction)`
A MESSAGE_COMPONENT interaction: someone clicked a button or chose from a select menu.

- fields: data: MessageComponentData, message: dict[str, object]

### `class UnknownInteraction(Interaction)`
An interaction type without its own subclass yet (PING, MODAL_SUBMIT); ``data`` stays untyped.

- fields: data: Mapping[str, object] | None

### `class Message(DiscordModel)`
MESSAGE_CREATE (subset - https://docs.discord.com/developers/resources/message).

- fields: id: Snowflake, channel_id: Snowflake, guild_id: Snowflake | None, author: User, content: str, timestamp: str,
  edited_timestamp: str | None, tts: bool, mention_everyone: bool

### `class EventName(StrEnum)`
Every dispatch event name Discord currently defines.

- fields: model: type[DiscordModel] | None
- attributes: READY, MESSAGE_CREATE, GUILD_CREATE, INTERACTION_CREATE, RESUMED, APPLICATION_COMMAND_PERMISSIONS_UPDATE,
  AUTO_MODERATION_RULE_CREATE, AUTO_MODERATION_RULE_UPDATE, AUTO_MODERATION_RULE_DELETE,
  AUTO_MODERATION_ACTION_EXECUTION, CHANNEL_CREATE, CHANNEL_UPDATE, CHANNEL_DELETE, CHANNEL_PINS_UPDATE, THREAD_CREATE,
  THREAD_UPDATE, THREAD_DELETE, THREAD_LIST_SYNC, THREAD_MEMBER_UPDATE, THREAD_MEMBERS_UPDATE, ENTITLEMENT_CREATE,
  ENTITLEMENT_UPDATE, ENTITLEMENT_DELETE, GUILD_UPDATE, GUILD_DELETE, GUILD_AUDIT_LOG_ENTRY_CREATE, GUILD_BAN_ADD,
  GUILD_BAN_REMOVE, GUILD_EMOJIS_UPDATE, GUILD_STICKERS_UPDATE, GUILD_INTEGRATIONS_UPDATE, GUILD_MEMBER_ADD,
  GUILD_MEMBER_REMOVE, GUILD_MEMBER_UPDATE, GUILD_MEMBERS_CHUNK, GUILD_ROLE_CREATE, GUILD_ROLE_UPDATE,
  GUILD_ROLE_DELETE, GUILD_SCHEDULED_EVENT_CREATE, GUILD_SCHEDULED_EVENT_UPDATE, GUILD_SCHEDULED_EVENT_DELETE,
  GUILD_SCHEDULED_EVENT_USER_ADD, GUILD_SCHEDULED_EVENT_USER_REMOVE, GUILD_SOUNDBOARD_SOUND_CREATE,
  GUILD_SOUNDBOARD_SOUND_UPDATE, GUILD_SOUNDBOARD_SOUND_DELETE, GUILD_SOUNDBOARD_SOUNDS_UPDATE, SOUNDBOARD_SOUNDS,
  INTEGRATION_CREATE, INTEGRATION_UPDATE, INTEGRATION_DELETE, INVITE_CREATE, INVITE_DELETE, MESSAGE_UPDATE,
  MESSAGE_DELETE, MESSAGE_DELETE_BULK, MESSAGE_REACTION_ADD, MESSAGE_REACTION_REMOVE, MESSAGE_REACTION_REMOVE_ALL,
  MESSAGE_REACTION_REMOVE_EMOJI, MESSAGE_POLL_VOTE_ADD, MESSAGE_POLL_VOTE_REMOVE, PRESENCE_UPDATE,
  STAGE_INSTANCE_CREATE, STAGE_INSTANCE_UPDATE, STAGE_INSTANCE_DELETE, SUBSCRIPTION_CREATE, SUBSCRIPTION_UPDATE,
  SUBSCRIPTION_DELETE, TYPING_START, USER_UPDATE, VOICE_CHANNEL_EFFECT_SEND, VOICE_CHANNEL_START_TIME_UPDATE,
  VOICE_CHANNEL_STATUS_UPDATE, VOICE_STATE_UPDATE, VOICE_SERVER_UPDATE, WEBHOOKS_UPDATE

## `wd_discord.gateway.presence` — `wd-discord/src/wd_discord/gateway/presence.py`
Presences and activities as the gateway sends them (https://docs.discord.com/developers/events/gateway-events#presence).

### `class Status(StrEnum)`
Valid presence statuses (https://docs.discord.com/developers/topics/gateway-events#update-presence-status-types).

- attributes: online, dnd, idle, invisible, offline

### `class ActivityType(IntEnum)`
https://docs.discord.com/developers/events/gateway-events#activity-object-activity-types.

- attributes: PLAYING, STREAMING, LISTENING, WATCHING, CUSTOM, COMPETING

### `class ActivityFlags(IntFlag)`
https://docs.discord.com/developers/events/gateway-events#activity-object-activity-flags.

- attributes: INSTANCE, JOIN, SPECTATE, JOIN_REQUEST, SYNC, PLAY, PARTY_PRIVACY_FRIENDS, PARTY_PRIVACY_VOICE_CHANNEL,
  EMBEDDED

### `class ActivityTimestamps(DiscordModel)`
When an activity started and ends, as Unix milliseconds.

- fields: start: int | None, end: int | None

### `class ActivityEmoji(DiscordModel)`
The emoji of a custom status.

- fields: name: str, id: Snowflake | None, animated: bool | None

### `class ActivityParty(DiscordModel)`
The party a user is in for an activity.

- fields: id: str | None, size: tuple[int, int] | None

### `class ActivityAssets(DiscordModel)`
The images an activity shows, with their hover texts.

- fields: large_image: str | None, large_text: str | None, large_url: str | None, small_image: str | None, small_text:
  str | None, small_url: str | None, invite_cover_image: str | None

### `class ActivitySecrets(DiscordModel)`
The secrets for joining or spectating an activity.

- fields: join: str | None, spectate: str | None, match: str | None

### `class Activity(DiscordModel)`
https://docs.discord.com/developers/events/gateway-events#activity-object.

- fields: name: str, type: ActivityType, url: str | None, created_at: int, timestamps: ActivityTimestamps | None,
  application_id: Snowflake | None, status_display_type: int | None, details: str | None, details_url: str | None,
  state: str | None, state_url: str | None, emoji: ActivityEmoji | None, party: ActivityParty | None, assets:
  ActivityAssets | None, secrets: ActivitySecrets | None, instance: bool | None, flags: ActivityFlags | None, buttons:
  list[str] | None

### `class ClientStatus(DiscordModel)`
A user's status per platform; a platform they're offline or invisible on is left out.

- fields: desktop: Status | None, mobile: Status | None, web: Status | None, vr: Status | None

### `class PresenceUser(DiscordModel)`
The user a presence is for: only ``id`` is certain, any other user field may come along.

- fields: id: Snowflake, username: str | None, discriminator: str | None, global_name: str | None, avatar: ImageHash |
  None, bot: bool | None, system: bool | None, banner: ImageHash | None, accent_color: int | None, flags: int | None,
  public_flags: int | None, avatar_decoration_data: Avatar | None, collectibles: Collectibles | None, primary_guild:
  UserPrimaryGuild | None

### `class Presence(DiscordModel)`
https://docs.discord.com/developers/events/gateway-events#presence-update-presence-update-event-fields.

- fields: user: PresenceUser, guild_id: Snowflake | None, status: Status, activities: list[Activity], client_status:
  ClientStatus

## `wd_discord.gateway.sharding` — `wd-discord/src/wd_discord/gateway/sharding.py`
Gateway sharding (https://docs.discord.com/developers/events/gateway#sharding).

- module names: GATEWAY_URL_QUERY, IDENTIFY_BATCH_DELAY
- `shard_id_for_guild(guild_id: int, num_shards: int) -> int` — Return the shard a guild's events are routed to: ``(guild_id >> 22) % num_shards``.
- `rate_limit_key(shard_id: int, max_concurrency: int) -> int` — Return a shard's IDENTIFY rate-limit bucket: ``shard_id % max_concurrency``.
- `identify_batches(shard_ids: list[int], max_concurrency: int) -> list[list[int]]` — Group ``shard_ids`` (ascending) into batches that may IDENTIFY concurrently.
- `parse_gateway_bot(payload: dict[str, Any]) -> GatewayBotInfo` — Parse a ``GET /gateway/bot`` JSON body into a :class:`GatewayBotInfo` (API -> object).
- `async fetch_gateway_bot(client: Client) -> GatewayBotInfo | ApiResponseError | RequestError` — Fetch ``GET /gateway/bot``, passing request errors through as values.

### `class SessionStartLimit(DiscordModel)`
The ``session_start_limit`` object from ``GET /gateway/bot``.

- fields: total: int, remaining: int, reset_after: int, max_concurrency: int

### `class GatewayBotInfo(DiscordModel)`
The ``GET /gateway/bot`` response (API -> object via :func:`parse_gateway_bot`).

- fields: url: str, shards: int, session_start_limit: SessionStartLimit
- `@property connect_url -> str` — The WSS URL with the version/encoding query this library speaks.

### `class ShardManager`
Run one :class:`Gateway` per shard, respecting the IDENTIFY rate limits.

- `@with_known_exception shard_for_guild(guild_id: int) -> Gateway | RuntimeError` — Return the started shard handling ``guild_id``'s events, or the :class:`RuntimeError` if not started.
- `async serve_forever(dispatch: Callable[[str, DiscordModel], Awaitable[None]]) -> None` — Run every shard's receive loop until cancelled.
