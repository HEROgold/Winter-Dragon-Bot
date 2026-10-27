<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord` (wd-discord)
wd-discord: a small Discord API (v10) client library for Winter Dragon.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord` — `wd-discord/src/wd_discord/__init__.py`

- exports: URLS, AnyGuildInteraction, AnyInteraction, ApiResponseError, Application, AuditLogReason,
  AutocompleteInteraction, BoundEvent, Channel, ChannelPinsUpdate, ChannelType, Client, Color, CommandInteraction,
  ComponentInteraction, CurrentUser, DiscordModel, Embed, EmbedField, Emoji, Entitlement, EventName, Gateway,
  GatewayActivity, GatewayBotInfo, GatewayGuild, GlobalCommand, Guild, GuildCommand, GuildCommandInteraction,
  GuildComponentInteraction, GuildCreate, GuildDelete, GuildEmojisUpdate, GuildStickersUpdate, Interaction, Invite,
  Member, MemberRemove, MembersChunk, Message, MessageDelete, MessageDeleteBulk, ModalSubmitInteraction, NetworkError,
  PartialChannel, PartialEmoji, PartialGlobalCommand, PartialGuild, PartialGuildCommand, PartialMember, PartialMessage,
  PartialRole, PartialUser, PermissionOverwrite, Permissions, Presence, RawEvent, ReactionAdd, ReactionRemove,
  ReactionRemoveAll, ReactionRemoveEmoji, Ready, Resolved, Role, Sentry, ShardManager, Snowflake, Status, Sticker, Team,
  TeamMember, ThreadCreate, ThreadDelete, ThreadListSync, ThreadMember, ThreadMembersUpdate, Token, TokenType,
  TypingStart, UnknownInteraction, User, VoiceChannelStartTimeUpdate, VoiceChannelStatusUpdate, VoiceState, bind,
  is_gone, is_network_error, narrow_to_guild

## `wd_discord.audit` — `wd-discord/src/wd_discord/audit.py`
Audit-log reasons (https://docs.discord.com/developers/resources/audit-log#audit-log-entry-object).

- module names: REASON_HEADER
- `type Reason = AuditLogReason | str | None`
- `reason_headers(reason: Reason) -> dict[str, str]` — Return the headers for ``reason``: none without one, else the audit-log reason header.

### `@dataclass class AuditLogReason`
Why the bot made a change, as shown in the guild's audit log.

- fields: text: str
- `headers() -> dict[str, str]` — Return the request header carrying this reason, cut to :data:`~wd_discord.limits.MAX_REASON_LENGTH` with :func:`~wd_discord.limits.truncate` and URL-encoded.

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

## `wd_discord.cache` — `wd-discord/src/wd_discord/cache.py`
The client's view of Discord, kept current by the gateway.

### `@dataclass class GuildState`
What the client knows of one guild.

- fields: guild: Guild, unavailable: bool, channels: dict[Snowflake, Channel] | None, threads: dict[Snowflake, Channel]
  | None, roles: dict[Snowflake, Role], emojis: dict[Snowflake, Emoji], stickers: dict[Snowflake, Sticker], members:
  dict[Snowflake, GuildMember], members_complete: bool, voice_states: dict[Snowflake, VoiceState] | None, presences:
  dict[Snowflake, Presence] | None
- `current_guild() -> Guild` — Return the guild's data with its roles, emojis and stickers as they are now, not as it was sent.
- `set_guild(guild: Guild) -> None` — Take ``guild`` as the guild's data, with the roles, emojis and stickers it carries.

### `class StateCache`
Every guild, channel and the bot's own user, as the gateway last described them.

- `guild(guild_id: Snowflake) -> GuildState | None` — Return what's known of the guild ``guild_id``, or ``None``.
- `channel(channel_id: Snowflake) -> Channel | None` — Return the guild channel, thread or DM ``channel_id``, or ``None``.
- `store_guild(guild: Guild) -> None` — Take a fetched ``guild`` as the latest data of it, with its roles, emojis and stickers.
- `store_channels(guild_id: Snowflake, channels: Iterable[Channel]) -> None` — Take ``channels`` as every channel of a known guild, threads excluded.
- `store_roles(guild_id: Snowflake, roles: Iterable[Role]) -> None` — Take ``roles`` as every role of a known guild.
- `store_emojis(guild_id: Snowflake, emojis: Iterable[Emoji]) -> None` — Take ``emojis`` as every custom emoji of a known guild.
- `store_stickers(guild_id: Snowflake, stickers: Iterable[Sticker]) -> None` — Take ``stickers`` as every sticker of a known guild.
- `store_members(guild_id: Snowflake, members: Iterable[GuildMember]) -> None` — Add or replace ``members`` of a known guild; the others stay as they were.
- `apply(model: DiscordModel) -> DiscordModel | None` — Bring the cache up to date with a parsed dispatch ``model``.

## `wd_discord.client` — `wd-discord/src/wd_discord/client.py`
The built-in Discord REST client for wd-discord.

- `type NetworkError = ApiResponseError | RequestError`
- `type RequestResult = Response | NetworkError`
- `type InflightKey = tuple[str, tuple[tuple[str, str], ...]]`
- `returns_known_exception[**P, T, E: Exception](*exceptions: type[E]) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T | E]]]` — Async analog of :func:`herogold.errors.with_known_exception`.
- `is_network_error(value: object) -> TypeIs[NetworkError]` — Whether ``value`` is a failed request: a Discord API error or a network error.
- `is_gone(result: object) -> bool` — Whether a delete answering ``result`` left the resource gone: it worked, or the resource was gone already.

### `@dataclass class Received`
A gateway dispatch as :meth:`Client.receive` took it.

- fields: event: BoundEvent | DiscordModel, previous: DiscordModel | None

### `class Client(LoggerMixin)`
An async Discord REST client pinned to the configured API version (v10 by default).

- `async aclose() -> None` — Close the underlying httpxyz transport.
- `@returns_known_exception async request(method: str, route: Template, *, cache: bool=False, **kwargs: Unpack[RequestKwargs]) -> Response | ApiResponseError` — Send a request, returning the :class:`Response` or a parsed error value.
- `async get(route: Template, *, cache: bool=False, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a GET request; with ``cache``, reuse a recent answer to it (see :meth:`request`).
- `async post(route: Template, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a POST request.
- `async patch(route: Template, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a PATCH request.
- `async put(route: Template, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a PUT request.
- `async delete(route: Template, **kwargs: Unpack[RequestKwargs]) -> RequestResult` — Send a DELETE request.
- `receive(model: DiscordModel) -> Received` — Take a parsed gateway dispatch: bring :attr:`cache` up to date with it, then bind it to this client.
- `async get_gateway_bot() -> GatewayBotInfo | NetworkError` — GET /gateway/bot - the gateway WebSocket URL + recommended shard/session info.
- `async get_shard_manager(info: GatewayBotInfo, *, intents: Intents | None=None) -> ShardManager` — Return an unstarted :class:`ShardManager` for the given :class:`GatewayBotInfo`.

## `wd_discord.color` — `wd-discord/src/wd_discord/color.py`
Discord's RGB color, an integer on the wire.

- module names: MAX_COLOR

### `class Color(int)`
An RGB color, ``0x000000`` to ``0xFFFFFF``; still an ``int``, so it goes on the wire unchanged.

- `@classmethod from_hex(text: str) -> Color` — Parse ``"#00ff00"``, ``"00ff00"`` or ``"0x00ff00"``.

## `wd_discord.components` — `wd-discord/src/wd_discord/components.py`
Legacy message components: action rows and buttons (https://docs.discord.com/developers/components/reference).

- `type CustomId = str`
- `components_payload(rows: Sequence[ActionRow]) -> list[ActionRow]` — Return the ``components`` JSON for a message, checking the message-wide limits.

### `class ComponentType(OpenIntEnum)`
The type of a component.

- attributes: ACTION_ROW, BUTTON, STRING_SELECT, TEXT_INPUT, USER_SELECT, ROLE_SELECT, MENTIONABLE_SELECT,
  CHANNEL_SELECT, SECTION, TEXT_DISPLAY, THUMBNAIL, MEDIA_GALLERY, FILE, SEPARATOR, CONTAINER, LABEL, FILE_UPLOAD,
  RADIO_GROUP, CHECKBOX_GROUP, CHECKBOX

### `class ButtonStyle(OpenIntEnum)`
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

### `class TextInputStyle(OpenIntEnum)`
How tall a text input is.

- attributes: SHORT, PARAGRAPH

### `class TextInput(BaseModel)`
A text field inside a :class:`Label` of a :class:`Modal`.

- fields: type: Literal[ComponentType.TEXT_INPUT], custom_id: CustomId, style: TextInputStyle, min_length: int | None,
  max_length: int | None, required: bool | None, value: str | None, placeholder: str | None
- attributes: model_config

### `class Label(BaseModel)`
A caption above one component of a :class:`Modal`.

- fields: type: Literal[ComponentType.LABEL], label: str, description: str | None, component: TextInput
- attributes: model_config

### `class Modal(BaseModel)`
A pop-up form, shown as the response to an interaction.

- fields: custom_id: CustomId, title: str, components: list[Label]
- attributes: model_config

## `wd_discord.constants` — `wd-discord/src/wd_discord/constants.py`
Constants used throughout the library.

- module names: DISCORD_EPOCH

## `wd_discord.embed` — `wd-discord/src/wd_discord/embed.py`
A minimal Discord embed model.

### `class EmbedField(DiscordModel)`
One entry in an embed's ``fields`` array.

- fields: name: str, value: str, inline: bool

### `class EmbedFooter(DiscordModel)`
The footer shown under an embed.

- fields: text: str, icon_url: str | None

### `class Embed(DiscordModel)`
A Discord message embed (minimal subset - see module docstring for what's missing).

- fields: title: str | None, description: str | None, color: Color | None, fields: list[EmbedField] | None, footer:
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

### `class ImageFormats(StrEnum)`
Valid image formats supported by Discord.

- attributes: JPG, JPEG, PNG, WebP, GIF, Lottie

### `class ImageHash`
https://docs.discord.com/developers/reference#image-formatting.

- `@property base_url -> str` — The configured CDN host (:attr:`~wd_config.discord.URLS.cdn`), with a trailing slash.
- `url(path: str, fmt: ImageFormats=ImageFormats.PNG) -> str` — Return the CDN URL of this image under ``path`` (e.g. ``avatars/{user_id}``) in format ``fmt``.

## `wd_discord.intents` — `wd-discord/src/wd_discord/intents.py`
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
  auto_moderation, GUILD_MESSAGE_POLLS, guild_polls, DIRECT_MESSAGE_POLLS, dm_polls, polls, THREAD_MEMBERS_UPDATE,
  MESSAGE_CREATE, MESSAGE_UPDATES, MESSAGE_DELETE, CHANNEL_PINS_UPDATE, MESSAGE_POLL_VOTE_REMOVE, MESSAGE_REACTION_ADD,
  MESSAGE_REACTION_REMOVE, MESSAGE_REACTION_REMOVE_ALL, MESSAGE_REACTION_REMOVE_EMOJI, TYPING_START,
  MESSAGE_POLL_VOTE_ADD
- `@classmethod none() -> Intents` — Return an Intents object with no intents set.
- `@classmethod all() -> Intents` — Return an Intents object with all intents set.

## `wd_discord.interactions` — `wd-discord/src/wd_discord/interactions.py`
Discord application commands (https://docs.discord.com/developers/interactions/application-commands).

- module names: CHAT_INPUT_NAME_PATTERN
- `type Name = str`
- `type ChatInputName = str`
- `type Description = str`
- `type Localizations = dict[Locale, str]`

### `class ApplicationCommandType(OpenIntEnum)`
Represents the type of an application command.

- attributes: CHAT_INPUT, USER, MESSAGE, PRIMARY_ENTRY_POINT

### `class ApplicationCommandOptionType(OpenIntEnum)`
Represents the type of an application command option (distinct from the command's own type).

- attributes: SUB_COMMAND, SUB_COMMAND_GROUP, STRING, INTEGER, BOOLEAN, USER, CHANNEL, ROLE, MENTIONABLE, NUMBER,
  ATTACHMENT

### `class InteractionContextType(OpenIntEnum)`
Where an application command can be used.

- attributes: GUILD, BOT_DM, PRIVATE_CHANNEL

### `class ApplicationIntegrationType(OpenIntEnum)`
Where an app can be installed, and so where its commands are available.

- attributes: GUILD_INSTALL, USER_INSTALL

### `class EntryPointCommandHandlerType(OpenIntEnum)`
Who handles a PRIMARY_ENTRY_POINT command's interaction.

- attributes: APP_HANDLER, DISCORD_LAUNCH_ACTIVITY

### `class Locale(OpenStrEnum)`
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
- `to_params() -> ApplicationCommandParams` — Return the create/edit body that defines this command, without the fields only Discord sets.

### `class ApplicationCommandParams(BaseModel)`
The JSON body for creating or editing an application command.

- fields: name: Name, name_localizations: Localizations | None, description: str, description_localizations:
  Localizations | None, options: list[ApplicationCommandOption] | None, default_member_permissions: Permissions | None,
  integration_types: list[ApplicationIntegrationType] | None, contexts: list[InteractionContextType] | None, type:
  ApplicationCommandType, nsfw: bool | None, handler: EntryPointCommandHandlerType | None
- attributes: model_config
- `to_json() -> JsonPayload` — Return the request body.

## `wd_discord.limits` — `wd-discord/src/wd_discord/limits.py`
Discord's documented limits, and :func:`truncate` to fit text into one of them.

- module names: ELLIPSIS, MAX_ACTION_ROW_BUTTONS, MAX_MESSAGE_COMPONENTS, MAX_CUSTOM_ID_LENGTH, MAX_BUTTON_LABEL_LENGTH,
  MAX_MODAL_TITLE_LENGTH, MAX_LABEL_LENGTH, MAX_TEXT_INPUT_LENGTH, MAX_EMBED_FIELDS, MAX_EMBED_CHARACTERS,
  MAX_EMBED_TITLE_LENGTH, MAX_EMBED_DESCRIPTION_LENGTH, MAX_EMBED_FIELD_NAME_LENGTH, MAX_EMBED_FIELD_VALUE_LENGTH,
  MAX_OPTIONS, MAX_CHOICES, MAX_CHOICE_NAME_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_REASON_LENGTH, MAX_USER_LIMIT,
  MAX_CHANNEL_NAME_LENGTH, MIN_GUILD_NAME_LENGTH, MAX_GUILD_NAME_LENGTH, MAX_MESSAGES_PER_PAGE, MAX_MEMBERS_PER_PAGE
- `truncate(text: str, limit: int) -> str` — Return ``text``, or when it's longer than ``limit`` characters, its start cut to fit ``limit`` with :data:`ELLIPSIS`.

## `wd_discord.log` — `wd-discord/src/wd_discord/log.py`
Module-level loggers that reach a log file.

- `@cache get_logger(name: str) -> Logger` — Return the logger for ``name``, the same one on every call, writing to ``logs/<name>.log``.

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

## `wd_discord.open_enum` — `wd-discord/src/wd_discord/open_enum.py`
Enums for values Discord owns, which accept a value Discord adds later instead of refusing the payload.

### `class OpenIntEnum(IntEnum)`
An IntEnum of Discord's values: an unknown int becomes a member named ``UNKNOWN_<value>``.

### `class OpenStrEnum(StrEnum)`
A StrEnum of Discord's values: an unknown string becomes a member named after it.

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

## `wd_discord.payloads` — `wd-discord/src/wd_discord/payloads.py`
Outbound request bodies and the keyword arguments :meth:`Client.request` accepts.

### `class JsonPayload(TypedDict, total=False)`
A JSON payload for a request.

- fields: recipient_id: str, max_age: int, max_uses: int, temporary: bool, unique: bool, username: str, avatar: str,
  banner: str, data: MessageData | ModalData, type: InteractionCallbackType, default_member_permissions: str,
  channel_id: str | None, nick: str | None, communication_disabled_until: str | None, delete_message_seconds: int,
  messages: list[str]

### `class OverwritePayload(TypedDict)`
A permission overwrite on a channel: what a role (``type`` 0) or member (``type`` 1) is allowed and denied.

- fields: id: str, type: int, allow: str, deny: str

### `class MemberPayload(TypedDict, total=False)`
The attributes of a guild member to change; ``None`` clears what Discord lets clear.

- fields: nick: str | None, roles: list[str] | None, mute: bool | None, deaf: bool | None, channel_id: str | None,
  communication_disabled_until: str | None, flags: int | None

### `class ChannelPayload(TypedDict, total=False)`
The settings of a guild channel to create or change.

- fields: name: str, type: int, topic: str, position: int, bitrate: int, user_limit: int, rate_limit_per_user: int,
  nsfw: bool, parent_id: str, permission_overwrites: list[OverwritePayload]

### `class RequestKwargs(TypedDict, total=False, closed=True)`
The keyword arguments accepted by :meth:`Client.request` and its convenience methods.

- fields: content: RequestContent, data: RequestData, files: RequestFiles, json: JsonPayload | MessageData |
  ChannelPayload | MemberPayload | OverwritePayload | list[JsonPayload], params: QueryParamTypes, headers: HeaderTypes,
  cookies: CookieTypes, auth: AuthTypes | UseClientDefault, follow_redirects: bool | UseClientDefault, timeout:
  TimeoutTypes | UseClientDefault, extensions: RequestExtensions

## `wd_discord.permission_solver` — `wd-discord/src/wd_discord/permission_solver.py`
Work out what a member may do in a guild or one of its channels, the way Discord does.

### `@dataclass class PermissionSolver`
The permissions ``member`` holds in ``guild``, and in each of its channels.

- fields: guild: Guild, member: GuildMember
- `@property member_id -> Snowflake` — The member's user ID.
- `base() -> Permissions` — Return the member's guild-wide permissions, before any channel overwrites.
- `can_give_role(role: Role) -> bool` — Whether the member may give ``role`` to someone, or take it away.
- `ungiveable_roles() -> Generator[Role]` — Yield the guild's roles the member can't give though someone could, highest first.
- `in_channel(channel: Channel) -> Permissions` — Return the member's permissions in ``channel``: :meth:`base` with its overwrites applied.

## `wd_discord.permissions` — `wd-discord/src/wd_discord/permissions.py`
Discord Permissions.

- module names: REQUIRES_2FA, TIMED_OUT_PERMISSIONS
- `type PermissionsField = Permissions`

### `class ChannelType(OpenIntEnum)`
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

- module names: logger, GLOBAL_REQUESTS_PER_SECOND, MAJOR_PARAM_PREFIXES
- `type RateLimiters = Mapping[RateLimitScope, RateLimiter]`
- `new_rate_limiters() -> dict[RateLimitScope, RateLimiter]` — Build a fresh limiter set for one client: its buckets start empty and are shared with no other client.

### `class RateLimitScope(StrEnum)`
The scope a rate limit applies to, named as in Discord's ``X-RateLimit-Scope`` header.

- attributes: USER, GLOBAL, SHARED

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

- `async acquire() -> None` — Wait on every limiter for this handler's route key before sending.
- `update(headers: Headers) -> None` — Update the rate limiters with the response headers for this handler's route key.
- `async wait_on_rate_limit(response: Response) -> None` — Parse a 429's body/headers and wait via the matching limiter before retrying.
- `async send[R: Response](func: Callable[[], CoroutineType[Any, Any, R]]) -> R` — Call ``func()`` under the rate-limit retry loop, retrying a 429 up to ``RateLimit.max_retries`` times.

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

### `class ModalData(TypedDict)`
The body of a MODAL response to an interaction (object -> API).

- fields: custom_id: str, title: str, components: list[dict[str, object]]

## `wd_discord.route` — `wd-discord/src/wd_discord/route.py`
REST routes written as PEP 750 templates: ``t"/channels/{channel_id}/messages"``.

### `@dataclass class Route`
One REST route: a template whose literal parts are the route and whose interpolations are its parameters.

- fields: template: Template
- `@property path -> str` — The request path, with each parameter formatted and percent-encoded as one path segment.
- `key(method: str) -> RouteKey` — Collapse this route to Discord's rate-limit route shape for ``method``.

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
