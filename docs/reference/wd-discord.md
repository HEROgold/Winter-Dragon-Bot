<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord` (wd-discord)
wd-discord: a small Discord API (v10) client library for Winter Dragon.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord` — `wd-discord/src/wd_discord/__init__.py`

- exports: URLS, AnyInteraction, ApiResponseError, Application, AutocompleteInteraction, BoundEvent, Channel,
  ChannelType, Client, CommandInteraction, ComponentInteraction, CurrentUser, DiscordModel, Embed, EmbedField,
  EventName, Gateway, GatewayActivity, GatewayBotInfo, GlobalCommand, Guild, GuildCreate, Interaction, Invite, Message,
  NetworkError, PartialChannel, PartialEmoji, PartialGlobalCommand, PartialGuild, PartialUser, Permissions, RawEvent,
  Ready, Sentry, ShardManager, Snowflake, Status, Token, TokenType, UnknownInteraction, User, bind, is_network_error

## `wd_discord.authenticate` — `wd-discord/src/wd_discord/authenticate.py`
Location for all authentication related functions and classes.

- `get_auth_header(type_: TokenType, token: Token) -> Template` — Get the authorization header for a given token.
- `get_bearer(token: Token) -> Template` — Get the bearer token header for a given token.
- `user_agent(url: URL, version: UserAgentVersion, metadata: MetaData) -> Template` — Get the user agent header for a given URL and version.
- `content_type(content_type: ContentType) -> Template` — Get the content type header for a given content type.
- `render(template: Template) -> str` — Render a PEP 750 ``Template`` into a plain string.
- `render_header(template: Template) -> tuple[str, str]` — Render a ``"Key: Value"`` header template into a ``(name, value)`` pair for httpxyz.

### `class Token(str)`
Represents a Discord bot token.

### `class TokenType(StrEnum)`
Represents the type of token being used for authentication.

- attributes: BOT

### `class UserAgentVersion(str)`
Represents the version of the user agent being used for authentication.

### `class URL(str)`
Represents a URL.

### `class MetaData(str)`
Represents metadata for the user agent.

### `class ContentType(StrEnum)`
Represents a content type.

- attributes: json, urlencoded, multipart

## `wd_discord.client` — `wd-discord/src/wd_discord/client.py`
The built-in Discord REST client for wd-discord.

- module names: DEFAULT_USER_AGENT_URL, DEFAULT_USER_AGENT_VERSION
- `type NetworkError = ApiResponseError | RequestError`
- `type RequestResult = Response | NetworkError`
- `returns_known_exception[**P, T, E: Exception](*exceptions: type[E]) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T | E]]]` — Async analog of :func:`herogold.errors.with_known_exception`.
- `is_network_error(value: object) -> TypeIs[NetworkError]` — Whether ``value`` is a failed request: a Discord API error or a network error.

### `class Client(LoggerMixin)`
An async Discord REST client pinned to the configured API version (v10 by default).

- `async aclose() -> None` — Close the underlying httpxyz transport.
- `@returns_known_exception async request(method: str, path: str, **kwargs: Unpack[RequestKwargs]) -> Response | ApiResponseError` — Send a request, returning the :class:`Response` or a parsed error value.
- `async get(path: str) -> RequestResult` — Send a GET request.
- `async post(path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a POST request.
- `async patch(path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a PATCH request.
- `async put(path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a PUT request.
- `async delete(path: str, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a DELETE request.
- `async get_gateway_bot() -> GatewayBotInfo | NetworkError` — GET /gateway/bot - the gateway WebSocket URL + recommended shard/session info.
- `async get_shard_manager(info: GatewayBotInfo, *, intents: Intents | None=None) -> ShardManager` — Return an unstarted :class:`ShardManager` for the given :class:`GatewayBotInfo`.

## `wd_discord.components` — `wd-discord/src/wd_discord/components.py`
Legacy message components: action rows and buttons (https://docs.discord.com/developers/components/reference).

- module names: MAX_ACTION_ROW_BUTTONS, MAX_MESSAGE_COMPONENTS, MAX_CUSTOM_ID_LENGTH
- `type CustomId = str`
- `components_payload(rows: Sequence[ActionRow]) -> list[ActionRow]` — Return the ``components`` JSON for a message, checking the message-wide limits.

### `class ComponentType(IntEnum)`
The type of a component.

- attributes: ACTION_ROW, BUTTON, STRING_SELECT, TEXT_INPUT, USER_SELECT, ROLE_SELECT, MENTIONABLE_SELECT,
  CHANNEL_SELECT, SECTION, TEXT_DISPLAY, THUMBNAIL, MEDIA_GALLERY, FILE, SEPARATOR, CONTAINER, LABEL, FILE_UPLOAD,
  RADIO_GROUP, CHECKBOX_GROUP, CHECKBOX

### `class ButtonStyle(IntEnum)`
How a button looks, and what clicking it does.

- attributes: PRIMARY, SECONDARY, SUCCESS, DANGER, LINK, PREMIUM

### `class Button(BaseModel)`
A clickable button; must sit inside an :class:`ActionRow`.

- fields: type: Literal[ComponentType.BUTTON], style: ButtonStyle, label: str | None, custom_id: CustomId | None,
  sku_id: Snowflake | None, url: str | None, disabled: bool
- attributes: model_config

### `class ActionRow(BaseModel)`
A row of up to 5 buttons at the bottom of a message.

- fields: type: Literal[ComponentType.ACTION_ROW], components: list[Button]
- attributes: model_config

## `wd_discord.constants` — `wd-discord/src/wd_discord/constants.py`
Constants used throughout the library.

- module names: DISCORD_EPOCH, RATE_LIMIT_BUCKET

## `wd_discord.embed` — `wd-discord/src/wd_discord/embed.py`
A minimal Discord embed model.

- module names: MAX_EMBED_FIELDS, MAX_EMBED_CHARACTERS

### `class EmbedField(DiscordModel)`
One entry in an embed's ``fields`` array.

- fields: name: str, value: str, inline: bool

### `class EmbedFooter(DiscordModel)`
The footer shown under an embed.

- fields: text: str, icon_url: str | None

### `class Embed(DiscordModel)`
A Discord message embed (minimal subset - see module docstring for what's missing).

- fields: title: str | None, description: str | None, color: int | None, fields: list[EmbedField] | None, footer:
  EmbedFooter | None
- `character_count() -> int` — Return how many characters count towards Discord's :data:`MAX_EMBED_CHARACTERS` limit.

## `wd_discord.files` — `wd-discord/src/wd_discord/files.py`
Files uploaded with a message (https://docs.discord.com/developers/reference#uploading-files).

- `attachments_payload(files: Sequence[File]) -> Generator[dict[str, object]]` — Yield the partial attachment object for each file, linking it to its ``files[n]`` form field by ``id``.
- `request_body(payload: JsonPayload | MessageData, files: Sequence[File]=()) -> RequestKwargs` — Return the request kwargs sending ``payload``: as JSON, or as ``multipart/form-data`` when there are ``files``.

### `@dataclass class File`
A file to upload with a message; Discord shows it as one of the message's attachments.

- fields: filename: str, data: bytes, description: str | None, content_type: str

## `wd_discord.image` — `wd-discord/src/wd_discord/image.py`
Discord CDN image hashes and formats (https://docs.discord.com/developers/reference#image-formatting).

### `class ImageHash`
https://docs.discord.com/developers/reference#image-formatting.

- attributes: base_url

### `class ImageFormats(StrEnum)`
Valid image formats supported by Discord.

- attributes: JPG, JPEG, PNG, WebP, GIF, Lottie

## `wd_discord.interactions` — `wd-discord/src/wd_discord/interactions.py`
Discord application commands (https://docs.discord.com/developers/interactions/application-commands).

- module names: MAX_OPTIONS, MAX_CHOICES, CHAT_INPUT_NAME_PATTERN
- `type Name = str`
- `type ChatInputName = str`
- `type Description = str`
- `type Localizations = dict[Locale, str]`

### `class ApplicationCommandType(IntEnum)`
Represents the type of an application command.

- attributes: CHAT_INPUT, USER, MESSAGE, PRIMARY_ENTRY_POINT

### `class ApplicationCommandOptionType(IntEnum)`
Represents the type of an application command option (distinct from the command's own type).

- attributes: SUB_COMMAND, SUB_COMMAND_GROUP, STRING, INTEGER, BOOLEAN, USER, CHANNEL, ROLE, MENTIONABLE, NUMBER,
  ATTACHMENT

### `class InteractionContextType(IntEnum)`
Where an application command can be used.

- attributes: GUILD, BOT_DM, PRIVATE_CHANNEL

### `class ApplicationIntegrationType(IntEnum)`
Where an app can be installed, and so where its commands are available.

- attributes: GUILD_INSTALL, USER_INSTALL

### `class EntryPointCommandHandlerType(IntEnum)`
Who handles a PRIMARY_ENTRY_POINT command's interaction.

- attributes: APP_HANDLER, DISCORD_LAUNCH_ACTIVITY

### `class Locale(StrEnum)`
A Discord locale code (https://docs.discord.com/developers/reference#locales).

- attributes: INDONESIAN, DANISH, GERMAN, ENGLISH_UK, ENGLISH_US, SPANISH, SPANISH_LATAM, FRENCH, CROATIAN, ITALIAN,
  LITHUANIAN, HUNGARIAN, DUTCH, NORWEGIAN, POLISH, PORTUGUESE_BRAZIL, ROMANIAN, FINNISH, SWEDISH, VIETNAMESE, TURKISH,
  CZECH, GREEK, BULGARIAN, RUSSIAN, UKRAINIAN, HINDI, THAI, CHINESE_CHINA, JAPANESE, CHINESE_TAIWAN, KOREAN

### `class ApplicationCommandOptionChoice(DiscordModel)`
One predefined value for a STRING, INTEGER or NUMBER option.

- fields: name: Description, name_localizations: Localizations | None, value: str | int | float

### `class ApplicationCommandOption(DiscordModel)`
A parameter of an application command, or one of its subcommands.

- fields: type: ApplicationCommandOptionType, name: ChatInputName, name_localizations: Localizations | None,
  description: Description, description_localizations: Localizations | None, required: bool, choices:
  list[ApplicationCommandOptionChoice] | None, options: list[ApplicationCommandOption] | None, channel_types:
  list[ChannelType] | None, min_value: int | float | None, max_value: int | float | None, min_length: int | None,
  max_length: int | None, autocomplete: bool | None, file_types: list[str] | None

### `class ApplicationCommand(DiscordModel)`
An application command as Discord returns it (list/create/edit response).

- fields: id: Snowflake, type: ApplicationCommandType, application_id: Snowflake, guild_id: Snowflake | None, name:
  Name, name_localizations: Localizations | None, description: str, description_localizations: Localizations | None,
  options: list[ApplicationCommandOption], default_member_permissions: PermissionsField | None, dm_permission: bool,
  default_permission: bool | None, nsfw: bool, integration_types: list[ApplicationIntegrationType] | None, contexts:
  list[InteractionContextType] | None, version: Snowflake, handler: EntryPointCommandHandlerType | None

### `class ApplicationCommandParams(BaseModel)`
The JSON body for creating or editing an application command.

- fields: name: Name, name_localizations: Localizations | None, description: str, description_localizations:
  Localizations | None, options: list[ApplicationCommandOption] | None, default_member_permissions: Permissions | None,
  integration_types: list[ApplicationIntegrationType] | None, contexts: list[InteractionContextType] | None, type:
  ApplicationCommandType, nsfw: bool | None, handler: EntryPointCommandHandlerType | None
- attributes: model_config
- `to_json() -> JsonPayload` — Return the request body.

## `wd_discord.models` — `wd-discord/src/wd_discord/models.py`
Shared pydantic base for all Discord API response models.

- module names: logger

### `class DiscordModel(BaseModel)`
Base for every Discord API response model.

- attributes: model_config

## `wd_discord.oauth` — `wd-discord/src/wd_discord/oauth.py`

### `class OAuthScopes(StrEnum)`
OAuth2 Scopes for the User Object.

- attributes: IDENTIFY, EMAIL, PREMIUM

## `wd_discord.pagination` — `wd-discord/src/wd_discord/pagination.py`
Pagination utilities for the Discord API.

- `snowflake_from_timestamp(timestamp: int) -> int` — Convert a Discord snowflake timestamp to a Snowflake timestamp.

## `wd_discord.partial_emoji` — `wd-discord/src/wd_discord/partial_emoji.py`
A minimal emoji reference carried by other Discord objects.

### `class PartialEmoji(DiscordModel)`
A minimal emoji reference: a custom emoji ``id`` or a unicode ``name``.

- fields: id: Snowflake | None, name: str | None, animated: bool | None
- `@property is_custom -> bool` — Whether this references a custom guild emoji (i.e. it has an ``id``).
- `@property is_unicode -> bool` — Whether this references a standard unicode emoji (a ``name`` but no ``id``).
- `@classmethod from_fields(emoji_id: Snowflake | None, emoji_name: str | None) -> PartialEmoji | None` — Build from a raw ``emoji_id`` / ``emoji_name`` pair; ``None`` when no emoji is set.

## `wd_discord.permissions` — `wd-discord/src/wd_discord/permissions.py`
Discord Permissions.

- `type PermissionsField = Permissions`

### `class ChannelType(IntEnum)`
Represents the different types of channels in Discord.

- attributes: GUILD_TEXT, DM, GUILD_VOICE, GROUP_DM, GUILD_CATEGORY, GUILD_ANNOUNCEMENT, ANNOUNCEMENT_THREAD,
  PUBLIC_THREAD, PRIVATE_THREAD, GUILD_STAGE_VOICE, GUILD_DIRECTORY, GUILD_FORUM, GUILD_MEDIA, T, Text, V, Voice, S,
  Stage

### `class Permissions(IntFlag)`
Represents the permissions a member has in a guild or channel.

- fields: CREATE_INSTANT_INVITE: Permissions.CREATE_INSTANT_INVITE, MANAGE_CHANNELS: Permissions.MANAGE_CHANNELS,
  PRIORITY_SPEAKER: Permissions.PRIORITY_SPEAKER, STREAM: Permissions.STREAM, VIEW_CHANNEL: Permissions.VIEW_CHANNEL,
  SEND_MESSAGES: Permissions.SEND_MESSAGES, SEND_TTS_MESSAGES: Permissions.SEND_TTS_MESSAGES, MANAGE_MESSAGES:
  Permissions.MANAGE_MESSAGES, EMBED_LINKS: Permissions.EMBED_LINKS, ATTACH_FILES: Permissions.ATTACH_FILES,
  READ_MESSAGE_HISTORY: Permissions.READ_MESSAGE_HISTORY, MENTION_EVERYONE: Permissions.MENTION_EVERYONE,
  USE_EXTERNAL_EMOJIS: Permissions.USE_EXTERNAL_EMOJIS, VIEW_GUILD_INSIGHTS: Permissions.VIEW_GUILD_INSIGHTS, CONNECT:
  Permissions.CONNECT, SPEAK: Permissions.SPEAK, MUTE_MEMBERS: Permissions.MUTE_MEMBERS, DEAFEN_MEMBERS:
  Permissions.DEAFEN_MEMBERS, MOVE_MEMBERS: Permissions.MOVE_MEMBERS, USE_VAD: Permissions.USE_VAD, MANAGE_ROLES:
  Permissions.MANAGE_ROLES, MANAGE_WEBHOOKS: Permissions.MANAGE_WEBHOOKS, USE_APPLICATION_COMMANDS:
  Permissions.USE_APPLICATION_COMMANDS, REQUEST_TO_SPEAK: Permissions.REQUEST_TO_SPEAK, MANAGE_EVENTS:
  Permissions.MANAGE_EVENTS, MANAGE_THREADS: Permissions.MANAGE_THREADS, CREATE_PUBLIC_THREADS:
  Permissions.CREATE_PUBLIC_THREADS, CREATE_PRIVATE_THREADS: Permissions.CREATE_PRIVATE_THREADS, USE_EXTERNAL_STICKERS:
  Permissions.USE_EXTERNAL_STICKERS, SEND_MESSAGES_IN_THREADS: Permissions.SEND_MESSAGES_IN_THREADS,
  USE_EMBEDDED_ACTIVITIES: Permissions.USE_EMBEDDED_ACTIVITIES, USE_SOUNDBOARD: Permissions.USE_SOUNDBOARD,
  CREATE_EVENTS: Permissions.CREATE_EVENTS, USE_EXTERNAL_SOUNDS: Permissions.USE_EXTERNAL_SOUNDS, SEND_VOICE_MESSAGES:
  Permissions.SEND_VOICE_MESSAGES, SET_VOICE_CHANNEL_STATUS: Permissions.SET_VOICE_CHANNEL_STATUS, SEND_POLLS:
  Permissions.SEND_POLLS, USE_EXTERNAL_APPS: Permissions.USE_EXTERNAL_APPS, PIN_MESSAGES: Permissions.PIN_MESSAGES,
  BYPASS_SLOWMODE: Permissions.BYPASS_SLOWMODE
- attributes: KICK_MEMBERS, BAN_MEMBERS, ADMINISTRATOR, MANAGE_GUILD, ADD_REACTIONS, VIEW_AUDIT_LOG, CHANGE_NICKNAME,
  MANAGE_NICKNAMES, MANAGE_GUILD_EXPRESSIONS, MODERATE_MEMBERS, VIEW_CREATOR_MONETIZATION_ANALYTICS,
  CREATE_GUILD_EXPRESSIONS
- `validate_channel(channel: ChannelType) -> bool` — Check if the permission is valid for the given channel type.
- `none() -> Permissions` — Return a Permissions object with no permissions set.
- `all() -> Permissions` — Return a Permissions object with all permissions set.

## `wd_discord.rate_limit` — `wd-discord/src/wd_discord/rate_limit.py`
Utilities for handling rate limits.

- module names: logger, GLOBAL_REQUESTS_PER_SECOND, MAX_RATE_LIMIT_RETRIES
- `route_key(method: str, path: str) -> RouteKey` — Collapse a request to Discord's major-param route-key shape (method + path).

### `class Buckets(StrEnum)`
Represents the different buckets for rate limits.

- attributes: global_, per_endpoint, per_user, shared

### `class ScopeError(BaseError)`
Raised when both _global and _scope are set or when neither are set in a HeaderFormat.

### `@dataclass class HeaderFormat`
Example header format for rate limits.

- fields: limit: int, remaining: int, reset: datetime, reset_after: timedelta, bucket: Buckets
- `@property scope -> str` — Get the scope of the rate limit.

### `class RateLimiter(ABC)`
A rate-limit strategy :class:`~wd_discord.client.Client` consults around each request.

- `async acquire(key: RouteKey) -> None` — Block until it's safe to send a request identified by ``key``.
- `update(key: RouteKey, headers: Mapping[str, str]) -> None` — Record any rate-limit state visible in a response's headers for ``key``.
- `async on_429(key: RouteKey, retry_after: float) -> None` — Handle being rate limited on ``key``: warn, then wait the fallback ``retry_after``.

### `@dataclass class GlobalRateLimiter(RateLimiter)`
Proactively caps outgoing requests to Discord's global rate limit.

- fields: limit: int
- `async acquire(key: RouteKey) -> None` — Wait until sending would keep the last second's request count under ``limit``.
- `update(key: RouteKey, headers: Mapping[str, str]) -> None` — No-op: Discord never sends a proactive global-remaining header.
- `async on_429(key: RouteKey, retry_after: float) -> None` — Fallback path: warn and wait Discord's own ``retry_after`` for the global limit.

### `@dataclass class BucketRateLimiter(RateLimiter)`
Proactively tracks per-route rate limits using Discord's ``X-RateLimit-*`` headers.

- `async acquire(key: RouteKey) -> None` — Wait until ``key``'s bucket resets, if a previously-learned bucket is exhausted.
- `update(key: RouteKey, headers: Mapping[str, str]) -> None` — Learn ``key``'s bucket id and refresh that bucket's remaining/reset from headers.
- `async on_429(key: RouteKey, retry_after: float) -> None` — Fallback path: warn and wait Discord's own ``retry_after`` for this route.

### `class SharedRateLimiter(RateLimiter)`
Reacts to shared-resource 429s (``X-RateLimit-Scope: shared``, e.g. emoji limits).

- `async acquire(key: RouteKey) -> None` — No-op: nothing to track ahead of time for a shared-resource limit.
- `update(key: RouteKey, headers: Mapping[str, str]) -> None` — No-op: same reasoning as :meth:`acquire`.
- `async on_429(key: RouteKey, retry_after: float) -> None` — Fallback path: warn and wait Discord's own ``retry_after`` for this shared resource.

### `class RouteKey(str)`
A string that uniquely identifies a Discord rate-limit bucket.

### `class MaxRetriesExceededError(Exception)`
Raised when a request exceeds the maximum number of rate-limit retries.

### `class RateLimitHandler(LoggerMixin)`
Runs a single logical request through the rate-limit retry loop.

- fields: limiters: ClassVar[dict[str, RateLimiter]]
- `async acquire() -> None` — Wait on every limiter for this handler's route key before sending.
- `update(headers: Headers) -> None` — Update the rate limiters with the response headers for this handler's route key.
- `async wait_on_rate_limit(response: Response) -> None` — Parse a 429's body/headers and wait via the matching limiter before retrying.
- `async send[R: Response](func: Callable[[], CoroutineType[Any, Any, R]]) -> R` — Call ``func()`` under the rate-limit retry loop, waking it up to :data:`MAX_RATE_LIMIT_RETRIES` times.

## `wd_discord.responses` — `wd-discord/src/wd_discord/responses.py`
Interaction responses (https://docs.discord.com/developers/interactions/receiving-and-responding).

- `message_data(*, content: str | None=None, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None, flags: MessageFlags | None=None, files: Sequence[File]=()) -> MessageData` — Build a message body for sending or editing a message (object -> API).

### `class InteractionCallbackType(IntEnum)`
The kind of initial response sent to an interaction.

- attributes: PONG, CHANNEL_MESSAGE_WITH_SOURCE, DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE, DEFERRED_UPDATE_MESSAGE,
  UPDATE_MESSAGE, APPLICATION_COMMAND_AUTOCOMPLETE_RESULT, MODAL, LAUNCH_ACTIVITY

### `class MessageFlags(IntFlag)`
Message flags an app can set when sending a message (subset).

- attributes: SUPPRESS_EMBEDS, EPHEMERAL, SUPPRESS_NOTIFICATIONS

### `class MessageData(TypedDict, total=False)`
The body of a response to an interaction (object -> API).

- fields: content: str, embeds: list[Embed], components: list[ActionRow], flags: MessageFlags, attachments:
  list[dict[str, object]], choices: list[dict[str, object]]

## `wd_discord.sentry` — `wd-discord/src/wd_discord/sentry.py`
Module to handle Sentry setup for wd-discord.

### `class Sentry`
A class to handle Sentry setup.

## `wd_discord.snowflake` — `wd-discord/src/wd_discord/snowflake.py`
Module for representing Discord Snowflakes, which are unique identifiers used by Discord for various entities.

- `type SnowflakeLike = Snowflake | int | str`

### `@dataclass class Snowflake`
Represents a Discord Snowflake, which is a unique identifier used by Discord for various entities.

- `@classmethod coerce(value: SnowflakeLike) -> Snowflake` — Return ``value`` as a :class:`Snowflake`.
- `@property timestamp -> datetime` — Get the timestamp from the snowflake.
- `@property worker_id -> int` — Get the worker ID from the snowflake.
- `@property process_id -> int` — Get the process ID from the snowflake.
- `@property increment -> int` — Get the increment from the snowflake.

## `wd_discord.testing` — `wd-discord/src/wd_discord/testing.py`
Test doubles for code built on wd-discord.

- module names: TEST_TOKEN, TEST_APPLICATION_ID, GUILD_JSON: Mapping[str, object]

### `@dataclass class SentRequest`
One request a :class:`RecordingClient` received.

- fields: method: str, path: str, json: Any, data: Any, files: Any

### `class RecordingClient(Client)`
A client that records requests instead of sending them, and answers with canned replies.

- `reply(method: str, path: str, body: Mapping[str, object] | list[Any] | None=None, *, status: int=200) -> None` — Answer every ``method`` request to ``path`` with ``body`` as JSON (no body when ``None``).
- `fail(method: str, path: str, error: ApiResponseError) -> None` — Answer every ``method`` request to ``path`` with ``error``.
- `requests_to(method: str, path: str) -> list[SentRequest]` — Return the recorded ``method`` requests to ``path``, oldest first.
- `interaction_responses() -> list[Any]` — Return the bodies of every initial interaction response sent, oldest first.
- `async request(method: str, path: str, **kwargs: Any) -> Response | ApiResponseError` — Record the request and return its canned reply.

## `wd_discord.timestamp` — `wd-discord/src/wd_discord/timestamp.py`
Discord timestamp markup: ``<t:EPOCH:STYLE>``, shown in each reader's own timezone and locale.

### `class TimestampStyle(StrEnum)`
How Discord renders a timestamp; the examples are for 2021-04-20 16:20:30 in an en-GB client.

- attributes: SHORT_TIME, MEDIUM_TIME, SHORT_DATE, LONG_DATE, LONG_DATE_SHORT_TIME, FULL_DATE_SHORT_TIME,
  SHORT_DATE_SHORT_TIME, SHORT_DATE_MEDIUM_TIME, RELATIVE_TIME

### `@dataclass class DiscordTime`
A moment, rendered as Discord timestamp markup.

- fields: moment: datetime
- `@property epoch -> int` — The moment in whole seconds since the Unix epoch, as Discord expects.
- `format(style: TimestampStyle | None=None) -> str` — Return the markup for this moment in ``style``, or in Discord's default style when not given.
- `with_relative(style: TimestampStyle=TimestampStyle.FULL_DATE_SHORT_TIME) -> str` — Return this moment in ``style``, followed by how long ago or from now it is: ``<t:E:F> (<t:E:R>)``.
