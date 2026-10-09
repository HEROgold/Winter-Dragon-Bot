<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_core` (wd-core)

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_core.client` — `wd-core/src/wd_core/client.py`
Domain specific web-client for WD.

### `class JsonPayload(TypedDict, total=False)`
A JSON payload for a request.

- fields: recipient_id: str, max_age: int, max_uses: int, temporary: bool, unique: bool, username: str, avatar: str,
  banner: str, data: MessageData, type: InteractionCallbackType, default_member_permissions: str, channel_id: str | None

### `class OverwritePayload(TypedDict)`
A permission overwrite on a channel: what a role (``type`` 0) or member (``type`` 1) is allowed and denied.

- fields: id: str, type: int, allow: str, deny: str

### `class ChannelPayload(TypedDict, total=False)`
The settings of a guild channel to create or change.

- fields: name: str, type: int, topic: str, position: int, bitrate: int, user_limit: int, rate_limit_per_user: int,
  nsfw: bool, parent_id: str, permission_overwrites: list[OverwritePayload]

### `class RequestKwargs(TypedDict, total=False)`
The keyword arguments accepted by :meth:`Client.request` and its convenience methods.

- fields: content: RequestContent, data: RequestData, files: RequestFiles, json: JsonPayload | MessageData |
  ChannelPayload | OverwritePayload | list[JsonPayload], params: QueryParamTypes, headers: HeaderTypes, cookies:
  CookieTypes, auth: AuthTypes | UseClientDefault, follow_redirects: bool | UseClientDefault, timeout: TimeoutTypes |
  UseClientDefault, extensions: RequestExtensions

### `class AsyncClient(_AsyncClient)`
Async client for WD.

## `wd_core.constants` — `wd-core/src/wd_core/constants.py`
Constants used across the bot.

- module names: intents, BOT_PERMISSIONS

## `wd_core.events` — `wd-core/src/wd_core/events.py`

### `class AuditLog(BaseModel)`
Database model for audit logs.

- fields: action: int, reason: str | None, target_id: str, category: int
- `@classmethod from_audit_log(entry: AuditLogEntry) -> Self` — Create an AuditLog instance from a Discord AuditLogEntry.

### `class AuditEvent(ABC)`
Base class for audit events.

- `@property category -> AuditLogAction` — Get the log category. lazily evaluated.
- `@property db_entry -> AuditLog` — Get the database entry. lazily evaluated.
- `async handle() -> None` — Handle the audit event.
- `async get_log_channels() -> Generator[LogChannel]` — Get the log channels for the guild.
- `async create_embed() -> Embed` — Create an embed for the audit event.

### `class LogChannel(GuildChannel, Messageable, ABC)`
A wrapper around GuildChannel to allow for easier logging.

- `async filter(action: AuditLogAction) -> bool` — Determine if a log should be sent to this channel based on the category.

### `class AuditEventHandler(LoggerMixin)`
Class for handling audit events.

- `async handle() -> None` — Handle the audit event.
- `async log(audit_action: AuditLogAction, embed: Embed, channels: Iterable[LogChannel]) -> None` — Dispatch a log to the appropriate channels/aggregators.

### `class AuditEventFactory`
Factory for creating audit events.

- fields: events: ClassVar[dict[AuditLogAction, list[type[AuditEvent]]]]
- `@classmethod register(action: AuditLogAction, event_type: type[AuditEvent]) -> None` — Register an audit event class for a category.
- `@classmethod get_events(entry: AuditLogEntry) -> Generator[AuditEvent]` — Get the audit event class for a category.

## `wd_core.intents` — `wd-core/src/wd_core/intents.py`
Module that contains the Gateway Intents.

- `type Decorator[**P, R] = Callable[P, R]`
- `type DecoratorFactory[**P, R] = Callable[[Callable[P, R]], Decorator[P, R]]`
- `requires_intents[**P, R](*required_intents: Intents, actual_intents: Intents | None=None) -> DecoratorFactory[P, R]` — Check if the required intents are enabled before executing the function.

### `class Intents(IntFlag)`
Represents the Gateway Intents.

- attributes: GUILDS, GUILD_CREATE, GUILD_UPDATE, GUILD_DELETE, GUILD_ROLE_CREATE, GUILD_ROLE_UPDATE, GUILD_ROLE_DELETE,
  CHANNEL_CREATE, CHANNEL_UPDATE, CHANNEL_DELETE, THREAD_CREATE, THREAD_UPDATE, THREAD_DELETE, THREAD_LIST_SYNC,
  THREAD_MEMBER_UPDATE, STAGE_INSTANCE_CREATE, STAGE_INSTANCE_UPDATE, STAGE_INSTANCE_DELETE,
  VOICE_CHANNEL_STATUS_UPDATE, VOICE_CHANNEL_START_TIME_UPDATE, guilds, GUILD_MEMBERS, GUILD_MEMBER_ADD,
  GUILD_MEMBER_UPDATE, GUILD_MEMBER_REMOVE, members, GUILD_MODERATION, GUILD_AUDIT_LOG_ENTRY_CREATE, GUILD_BAN_ADD,
  GUILD_BAN_REMOVE, moderation, bans, GUILD_EXPRESSIONS, GUILD_EMOJIS_UPDATE, GUILD_STICKERS_UPDATE,
  GUILD_SOUNDBOARD_SOUND_CREATE, GUILD_SOUNDBOARD_SOUND_UPDATE, GUILD_SOUNDBOARD_SOUND_DELETE,
  GUILD_SOUNDBOARD_SOUNDS_UPDATE, emojis, emojis_and_stickers, expressions, GUILD_INTEGRATIONS,
  GUILD_INTEGRATIONS_UPDATE, INTEGRATION_CREATE, INTEGRATION_UPDATE, INTEGRATION_DELETE, integrations, GUILD_WEBHOOKS,
  WEBHOOKS_UPDATE, webhooks, GUILD_INVITES, INVITE_CREATE, INVITE_DELETE, invites, GUILD_VOICE_STATES,
  VOICE_CHANNEL_EFFECT_SEND, VOICE_STATE_UPDATE, voice_states, GUILD_PRESENCES, PRESENCE_UPDATE, presences,
  GUILD_MESSAGES, MESSAGE_DELETE_BULK, guild_messages, GUILD_MESSAGE_REACTIONS, guild_reactions, GUILD_MESSAGE_TYPING,
  guild_typing, DIRECT_MESSAGES, dm_messages, messages, DIRECT_MESSAGE_REACTIONS, dm_reactions, reactions,
  DIRECT_MESSAGE_TYPING, dm_typing, typing, MESSAGE_CONTENT, message_content, GUILD_SCHEDULED_EVENTS,
  GUILD_SCHEDULED_EVENT_CREATE, GUILD_SCHEDULED_EVENT_UPDATE, GUILD_SCHEDULED_EVENT_DELETE,
  GUILD_SCHEDULED_EVENT_USER_ADD, GUILD_SCHEDULED_EVENT_USER_REMOVE, guild_scheduled_events,
  AUTO_MODERATION_CONFIGURATION, AUTO_MODERATION_RULE_CREATE, AUTO_MODERATION_RULE_UPDATE, AUTO_MODERATION_RULE_DELETE,
  auto_moderation_configuration, AUTO_MODERATION_EXECUTION, AUTO_MODERATION_ACTION_EXECUTION, auto_moderation_execution,
  auto_moderation, GUILD_MESSAGE_POLLS, dm_polls, DIRECT_MESSAGE_POLLS, guild_polls, polls, THREAD_MEMBERS_UPDATE,
  MESSAGE_CREATE, MESSAGE_UPDATES, MESSAGE_DELETE, CHANNEL_PINS_UPDATE, MESSAGE_POLL_VOTE_REMOVE, MESSAGE_REACTION_ADD,
  MESSAGE_REACTION_REMOVE, MESSAGE_REACTION_REMOVE_ALL, MESSAGE_REACTION_REMOVE_EMOJI, TYPING_START,
  MESSAGE_POLL_VOTE_ADD
- `@classmethod none() -> Intents` — Return an Intents object with no intents set.
- `@classmethod all() -> Intents` — Return an Intents object with all intents set.
- `@classmethod all2() -> Intents` — Return an Intents object with all intents set, except for privileged intents.

## `wd_core.package` — `wd-core/src/wd_core/package.py`
Module helping with importing modules for the Winter Dragon project.

- `get_package_version(package_name: str) -> PackageVersion` — Get the version of a package.

### `class PackageVersion(str)`
A string representing a package version.

## `wd_core.sentry` — `wd-core/src/wd_core/sentry.py`
Module to handle Sentry setup.

### `class Sentry`
A class to handle Sentry setup.
