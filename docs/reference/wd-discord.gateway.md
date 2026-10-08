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

### `class Status(StrEnum)`
Valid presence statuses (https://docs.discord.com/developers/topics/gateway-events#update-presence-status-types).

- attributes: online, dnd, idle, invisible, offline

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
  list[Channel], threads: list[Channel], members: list[GuildMember], voice_states: list[Mapping[str, object]],
  presences: list[Mapping[str, object]]

### `class InteractionType(IntEnum)`
The kind of interaction an INTERACTION_CREATE dispatch carries.

- attributes: PING, APPLICATION_COMMAND, MESSAGE_COMPONENT, APPLICATION_COMMAND_AUTOCOMPLETE, MODAL_SUBMIT

### `class ResolvedData(DiscordModel)`
The ``resolved`` block of interaction command data - full objects for referenced IDs.

- fields: users: dict[str, User] | None

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

### `class MessageCreatePayload(TypedDict)`
The raw ``d`` payload of a MESSAGE_CREATE dispatch, as delivered by the gateway (subset).

- fields: id: str, channel_id: str, guild_id: NotRequired[str], author: Mapping[str, object], content: str, timestamp:
  str, edited_timestamp: NotRequired[str | None], tts: bool, mention_everyone: bool

### `class ReadyPayload(TypedDict)`
The raw ``d`` payload of a READY dispatch, as delivered by the gateway (subset).

- fields: v: int, user: Mapping[str, object], guilds: list[Mapping[str, object]], session_id: str, resume_gateway_url:
  str, shard: NotRequired[list[int]], application: NotRequired[Mapping[str, object]]

### `class GuildCreatePayload(TypedDict)`
The raw ``d`` payload of a GUILD_CREATE dispatch, as delivered by the gateway (subset of the guild fields).

- fields: id: str, name: str, icon: str | None, owner_id: str, afk_timeout: int, roles: list[Mapping[str, object]],
  emojis: list[Mapping[str, object]], features: list[str], joined_at: NotRequired[str], large: NotRequired[bool],
  unavailable: NotRequired[bool], member_count: NotRequired[int], channels: NotRequired[list[Mapping[str, object]]],
  threads: NotRequired[list[Mapping[str, object]]], members: NotRequired[list[Mapping[str, object]]], voice_states:
  NotRequired[list[Mapping[str, object]]], presences: NotRequired[list[Mapping[str, object]]]

### `class InteractionCreatePayload(TypedDict)`
The raw ``d`` payload of an INTERACTION_CREATE dispatch, as delivered by the gateway (subset).

- fields: id: str, application_id: str, type: int, data: NotRequired[Mapping[str, object]], guild_id: NotRequired[str],
  channel_id: NotRequired[str], member: NotRequired[Mapping[str, object]], user: NotRequired[Mapping[str, object]],
  token: str, version: int

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
  SUBSCRIPTION_DELETE, TYPING_START, USER_UPDATE, VOICE_CHANNEL_EFFECT_SEND, VOICE_STATE_UPDATE, VOICE_SERVER_UPDATE,
  WEBHOOKS_UPDATE

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
