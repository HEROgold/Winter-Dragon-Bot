<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.entities` (wd-discord)
The high-level API: Discord objects bound to the client that acts on them, and the stores creating them.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.entities` — `wd-discord/src/wd_discord/entities/__init__.py`

- exports: AnyInteraction, AutocompleteInteraction, BaseChannel, BaseGlobalCommand, BaseGuild, BaseMember, BaseUser,
  BoundEvent, Channel, ClientBound, CommandInteraction, ComponentInteraction, CurrentApplication, CurrentUser, Entity,
  EntityStore, GlobalCommand, GlobalCommandStore, Guild, GuildCommand, GuildCommandStore, Interaction, Member, Message,
  Partial, PartialChannel, PartialGlobalCommand, PartialGuild, PartialMember, PartialUser, Ready, Store,
  UnknownInteraction, User, UserStore, VoiceState, bind, event_entities

## `wd_discord.entities.application` — `wd-discord/src/wd_discord/entities/application.py`
The application behind the client's token (https://docs.discord.com/developers/resources/application).

### `class CurrentApplication`
The client's own application: its data, its ID (which application-scoped routes need) and its commands.

- `async fetch() -> Application | NetworkError` — GET /applications/@me - the application object.
- `async id() -> Snowflake | NetworkError` — Return the application's ID, fetching and caching it when unknown.
- `guild_commands(guild_id: SnowflakeLike) -> GuildCommandStore` — Return the store of the application's commands registered in the guild ``guild_id``.

## `wd_discord.entities.base` — `wd-discord/src/wd_discord/entities/base.py`
Bases of the high-level API: client-bound entities and the stores that create them.

- `parse[M: DiscordModel](result: RequestResult, model: type[M]) -> M | NetworkError` — Return the failure in ``result``, or its JSON body validated as ``model``.
- `no_content(result: RequestResult) -> NetworkError | None` — Return the failure in ``result``, or ``None`` for an endpoint that answers without a body.

### `@dataclass class ClientBound`
Something that acts through a client, and wraps what the client returns in entities bound to it.

- fields: client: Client

### `@dataclass class Store(ClientBound)`
Client-scoped access point for one resource kind.

### `@dataclass class Entity[M: DiscordModel](ClientBound)`
A Discord object bound to the client that can act on it.

- fields: model: M

### `@dataclass class Partial[E](ClientBound, ABC)`
A Discord object known only by ID, which can act without fetching it first.

- fields: id: Snowflake
- `async fetch() -> E | NetworkError` — Fetch the full entity.

### `@dataclass class EntityStore[P: Partial[object]](Store)`
A store of one kind of entity that can be handled by ID: ``partial(id)`` and ``fetch(id)``.

- fields: partial_type: type[P]
- `partial(id: SnowflakeLike) -> P` — Return a handle on the object ``id``, without fetching it.
- `async fetch[E](id: SnowflakeLike) -> E | NetworkError` — Fetch the object ``id``.

## `wd_discord.entities.channel` — `wd-discord/src/wd_discord/entities/channel.py`
Channels (https://docs.discord.com/developers/resources/channel).

- module names: DEFAULT_INVITE_MAX_AGE

### `class BaseChannel(ClientBound)`
What can be done in a channel knowing only its ID: read, edit or delete it, send messages, set permissions.

- `@property mention -> str` — A clickable mention of the channel, as ``<#id>``.
- `async fetch() -> Channel | NetworkError` — GET /channels/{channel_id}.
- `async send(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> Message | NetworkError` — POST /channels/{channel_id}/messages - send a message; DM channels included.
- `async create_invite(*, max_age: int=DEFAULT_INVITE_MAX_AGE, max_uses: int=1, temporary: bool=False, unique: bool=True) -> Invite | NetworkError` — POST /channels/{channel_id}/invites - create an invite to this channel.
- `async edit(params: ChannelParams, *, reason: AuditLogReason | str | None=None) -> Channel | NetworkError` — PATCH /channels/{channel_id} - change the settings set in ``params``; needs MANAGE_CHANNELS.
- `async delete(*, reason: AuditLogReason | str | None=None) -> Channel | NetworkError` — DELETE /channels/{channel_id} - delete the channel, or close a DM; returns the deleted channel.
- `async set_permissions(overwrite: OverwriteParams, *, reason: AuditLogReason | str | None=None) -> NetworkError | None` — PUT /channels/{channel_id}/permissions/{overwrite_id} - set one role's or member's overwrite on the channel.
- `async delete_permissions(target_id: SnowflakeLike, *, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /channels/{channel_id}/permissions/{overwrite_id} - remove a role's or member's overwrite.

### `class Channel(Entity[ChannelModel], BaseChannel)`
A channel, as Discord returned it.

- `@property id -> Snowflake` — The channel's ID.
- `@property name -> str | None` — The channel's name; ``None`` for DM channels.
- `@property type -> ChannelType` — The kind of channel.
- `@property guild_id -> Snowflake | None` — The guild the channel belongs to; ``None`` for DM channels.
- `@property parent_id -> Snowflake | None` — The category a guild channel sits in, or the channel a thread was started in.

### `class PartialChannel(BaseChannel, Partial[Channel])`
A channel known only by ID.

## `wd_discord.entities.command` — `wd-discord/src/wd_discord/entities/command.py`
Application commands (https://docs.discord.com/developers/interactions/application-commands).

### `class BaseGlobalCommand(ClientBound)`
What can be done to a global command knowing only its ID: read it again, edit it, delete it.

- `async fetch() -> GlobalCommand | NetworkError` — GET /applications/{application_id}/commands/{command_id}.
- `async edit(params: ApplicationCommandParams) -> GlobalCommand | NetworkError` — PATCH /applications/{application_id}/commands/{command_id} - replace the command's definition.
- `async delete() -> NetworkError | None` — DELETE /applications/{application_id}/commands/{command_id}.

### `class GlobalCommand(Entity[ApplicationCommand], BaseGlobalCommand)`
A registered global command, as Discord returned it.

- `@property id -> Snowflake` — The command's ID.
- `@property name -> str` — The command's name.
- `@property version -> Snowflake` — Discord's auto-incrementing version of the definition; changes on every edit.
- `@property mention -> str` — A clickable mention of the command, as ``</name:id>``.

### `class PartialGlobalCommand(BaseGlobalCommand, Partial[GlobalCommand])`
A global command known only by ID, e.g. one stored from an earlier sync.

### `@dataclass class GlobalCommandStore(EntityStore[PartialGlobalCommand])`
The application's global commands: register, fetch and list them.

- `async path(command_id: SnowflakeLike | None=None) -> Template | NetworkError` — Return the global-commands route, or one command's, or the failure looking up the application ID.
- `async create(params: ApplicationCommandParams) -> GlobalCommand | NetworkError` — POST /applications/{application_id}/commands - register a new global command.
- `async fetch_all() -> Generator[GlobalCommand] | NetworkError` — GET /applications/{application_id}/commands - every registered global command.
- `async overwrite(params: Iterable[ApplicationCommandParams]) -> Generator[GlobalCommand] | NetworkError` — PUT /applications/{application_id}/commands - replace every global command with ``params``.

### `class GuildCommand(Entity[ApplicationCommand])`
A command registered in one guild, as Discord returned it.

- `@property id -> Snowflake` — The command's ID.
- `@property name -> str` — The command's name.
- `@property mention -> str` — A clickable mention of the command, as ``</name:id>``.

### `@dataclass class GuildCommandStore(Store)`
One guild's commands for the application: list them, or replace them all.

- fields: guild_id: Snowflake
- `async path() -> Template | NetworkError` — Return the guild-commands route, or the failure looking up the application ID.
- `async fetch_all() -> Generator[GuildCommand] | NetworkError` — GET /applications/{application_id}/guilds/{guild_id}/commands - every command registered in the guild.
- `async overwrite(params: Iterable[ApplicationCommandParams]) -> Generator[GuildCommand] | NetworkError` — PUT /applications/{application_id}/guilds/{guild_id}/commands - replace the guild's commands with ``params``.

## `wd_discord.entities.events` — `wd-discord/src/wd_discord/entities/events.py`
Gateway dispatch events bound to the client that received them.

- `type BoundEvent = AnyInteraction | Message | Guild | Ready | VoiceState`
- `bind(client: Client, model: DiscordModel) -> BoundEvent | DiscordModel` — Wrap a parsed dispatch ``model`` in the entity bound to ``client``, or return it as is if it has none.
- `event_entities() -> Mapping[EventName, type | TypeAliasType]` — Return the entity (or union of entities) :func:`bind` returns for each event; the source of ``listener.pyi``.

## `wd_discord.entities.guild` — `wd-discord/src/wd_discord/entities/guild.py`
Guilds (https://docs.discord.com/developers/resources/guild).

- module names: MAX_MEMBERS_PER_PAGE

### `class BaseGuild(ClientBound)`
What can be done to a guild knowing only its ID: read it, list and create its channels, list its members.

- `async fetch(*, with_counts: bool=False) -> Guild | NetworkError` — GET /guilds/{guild_id}; ``with_counts`` fills in the approximate member and online counts.
- `async channels() -> Generator[Channel] | NetworkError` — GET /guilds/{guild_id}/channels - the guild's channels, threads excluded.
- `async create_channel(params: GuildChannelParams, *, reason: AuditLogReason | str | None=None) -> Channel | NetworkError` — POST /guilds/{guild_id}/channels - create a channel or category; needs MANAGE_CHANNELS.
- `member(user_id: SnowflakeLike) -> PartialMember` — Return a handle on the member ``user_id`` of this guild, without fetching them.
- `async members(*, after: SnowflakeLike | None=None, limit: int=MAX_MEMBERS_PER_PAGE) -> Generator[Member] | NetworkError` — GET /guilds/{guild_id}/members - one page of members, by user ID, after the user ``after``.
- `async leave() -> NetworkError | None` — DELETE /users/@me/guilds/{guild_id} - remove the bot from the guild; fails for a guild it owns.

### `class Guild(Entity[GuildModel], BaseGuild)`
A guild, as Discord returned it.

- `@property id -> Snowflake` — The guild's ID.
- `@property name -> str` — The guild's name.
- `@property owner_id -> Snowflake` — The ID of the guild's owner.
- `@property afk_channel_id -> Snowflake | None` — The voice channel idle members are moved to, if the guild has one.

### `class PartialGuild(BaseGuild, Partial[Guild])`
A guild known only by ID.

## `wd_discord.entities.interaction` — `wd-discord/src/wd_discord/entities/interaction.py`
Interactions bound to the client that answers them.

- `type AnyInteraction = CommandInteraction | ComponentInteraction | AutocompleteInteraction | UnknownInteraction`

### `@dataclass class ResponseState`
Whether an interaction already got its one initial response.

- fields: responded: bool

### `@dataclass class Interaction[M: InteractionModel](Entity[M])`
The fields and responses every interaction shares.

- `@property id -> Snowflake` — The interaction's ID.
- `@property type -> InteractionType` — The kind of interaction.
- `@property token -> str` — The token for responding; valid for 15 minutes.
- `@property application_id -> Snowflake` — The ID of the application the interaction is for.
- `@property user -> User | None` — Who triggered the interaction, whether in a guild or a DM.
- `@property member -> GuildMember | None` — The invoking guild member, when invoked in a guild.
- `@property guild -> PartialGuild | None` — The guild the interaction was sent from, if any.
- `@property channel -> PartialChannel | None` — The channel the interaction was sent from, if any.
- `@property locale -> Locale | None` — The invoking user's language.
- `@property guild_locale -> Locale | None` — The guild's preferred language, when invoked in a guild.
- `@property app_permissions -> Permissions | None` — What the app may do where the interaction was sent.
- `@property context -> InteractionContextType | None` — Where the interaction was triggered from.
- `@property responded -> bool` — Whether the interaction already got its initial response.
- `async respond(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None, files: Sequence[File]=(), ephemeral: bool=False) -> NetworkError | None` — Reply with a message; ``ephemeral`` shows it only to the invoking user.
- `async defer(*, ephemeral: bool=False) -> NetworkError | None` — Acknowledge now and show a loading state; does nothing when already answered.
- `async edit_original(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None, files: Sequence[File]=()) -> Message | NetworkError` — PATCH /webhooks/{application_id}/{token}/messages/@original - edit the initial response.
- `async delete_original() -> NetworkError | None` — DELETE /webhooks/{application_id}/{token}/messages/@original - remove the initial response.
- `async followup(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None, files: Sequence[File]=(), ephemeral: bool=False) -> Message | NetworkError` — POST /webhooks/{application_id}/{token} - send another message after the initial response.

### `class CommandInteraction(Interaction[CommandInteractionModel])`
Someone ran an application command.

- `@property command_id -> Snowflake` — The ID of the command that ran.
- `@property command_name -> str` — The name of the command that ran.
- `@property options -> list[InteractionDataOption]` — The submitted option values; a subcommand's own values are nested in its option.
- `@property resolved -> ResolvedData | None` — Full objects for the IDs referenced by option values.

### `class ComponentInteraction(Interaction[ComponentInteractionModel])`
Someone clicked a button or chose from a select menu.

- `@property custom_id -> str` — The ``custom_id`` of the component that was used.
- `@property component_type -> ComponentType` — The kind of component that was used.
- `@property values -> list[str]` — The chosen values of a select menu; empty for buttons.
- `@property message -> Mapping[str, object]` — The message the component is attached to, as sent.
- `async update(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> NetworkError | None` — Edit the component's message as the initial response.
- `async defer_update() -> NetworkError | None` — Acknowledge now, without a loading state, and edit the component's message later; no-op once answered.

### `class AutocompleteInteraction(Interaction[AutocompleteInteractionModel])`
Someone is typing a value for an autocomplete option.

- `@property command_name -> str` — The name of the command being filled in.
- `@property options -> list[InteractionDataOption]` — The option values typed so far; the one being typed has ``focused`` set.
- `async suggest(choices: Sequence[ApplicationCommandOptionChoice]) -> NetworkError | None` — Offer ``choices`` (at most 25) for the focused option.

### `class UnknownInteraction(Interaction[InteractionModel])`
An interaction type without its own class yet (PING, MODAL_SUBMIT).

## `wd_discord.entities.member` — `wd-discord/src/wd_discord/entities/member.py`
Guild members (https://docs.discord.com/developers/resources/guild#guild-member-object).

### `class BaseMember(ClientBound)`
What can be done to a guild member knowing only their guild and user ID: read them, move them in voice.

- `@property mention -> str` — A clickable mention of the member, as ``<@id>``.
- `async fetch() -> Member | NetworkError` — GET /guilds/{guild_id}/members/{user_id}.
- `async move_to(channel_id: SnowflakeLike | None, *, reason: AuditLogReason | str | None=None) -> Member | NetworkError` — PATCH /guilds/{guild_id}/members/{user_id} - move the member to the voice channel ``channel_id``.

### `@dataclass class Member(Entity[GuildMember], BaseMember)`
A guild member, as Discord returned them; always with their user.

- fields: guild: Snowflake
- `@property guild_id -> Snowflake` — The guild the member is in.
- `@property id -> Snowflake` — The member's user ID.
- `@property bot -> bool` — Whether the member is a bot account.
- `@property display_name -> str` — The member's guild nickname, else their global display name, else their username.

### `@dataclass class PartialMember(BaseMember, Partial[Member])`
A guild member known only by guild and user ID.

- fields: guild: Snowflake
- `@property guild_id -> Snowflake` — The guild the member is in.

## `wd_discord.entities.message` — `wd-discord/src/wd_discord/entities/message.py`
Messages (https://docs.discord.com/developers/resources/message).

### `class Message(Entity[MessageModel])`
A message, as Discord returned or dispatched it.

- `@property id -> Snowflake` — The message's ID.
- `@property content -> str` — The message's text.
- `@property author -> User` — Who sent the message.
- `@property channel -> PartialChannel` — The channel the message was sent in.
- `async edit(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> Message | NetworkError` — PATCH /channels/{channel_id}/messages/{message_id} - edit a message the bot sent.
- `async delete() -> NetworkError | None` — DELETE /channels/{channel_id}/messages/{message_id}.

## `wd_discord.entities.ready` — `wd-discord/src/wd_discord/entities/ready.py`
The READY a shard receives once it has connected (https://docs.discord.com/developers/events/gateway-events#ready).

### `class Ready(Entity[ReadyModel])`
A shard finished connecting: who the bot is, and which guilds will follow as GUILD_CREATE.

- `@property user -> CurrentUser` — The user behind the client's token.
- `@property guilds -> Generator[PartialGuild]` — The guilds this shard serves; each one arrives in full later as a GUILD_CREATE.
- `@property session_id -> str` — The session ID, for resuming the connection.
- `@property shard -> tuple[int, int] | None` — The ``(shard_id, num_shards)`` of the shard that received it, when sharding.
- `@property application_id -> str | None` — The ID of the bot's application.

## `wd_discord.entities.user` — `wd-discord/src/wd_discord/entities/user.py`
Users (https://docs.discord.com/developers/resources/user).

### `class BaseUser(ClientBound)`
What can be done to a user knowing only their ID: read them, open a DM, message them.

- `@property mention -> str` — A clickable mention of the user, as ``<@id>``.
- `async fetch() -> User | NetworkError` — GET /users/{user_id}.
- `async dm() -> Channel | NetworkError` — POST /users/@me/channels - open the DM channel with this user, or return the one already open.
- `async send(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> Message | NetworkError` — Send this user a direct message, opening the DM channel first.

### `class User(Entity[UserModel], BaseUser)`
A user, as Discord returned or sent them.

- `@property id -> Snowflake` — The user's ID.
- `@property username -> str` — The user's username; not unique across the platform.
- `@property global_name -> str | None` — The user's display name, if set.
- `@property display_name -> str` — The name Discord shows for the user: their display name, else their username.
- `@property bot -> bool` — Whether the user belongs to an application.

### `class CurrentUser(User)`
The user behind the client's token.

- `async edit(*, username: str | None=None, avatar: ImageHash | None=None, banner: ImageHash | None=None) -> CurrentUser | NetworkError` — PATCH /users/@me - change the username, avatar or banner; a ``None`` argument leaves it unchanged.

### `class PartialUser(BaseUser, Partial[User])`
A user known only by ID.

### `@dataclass class UserStore(EntityStore[PartialUser])`
Users the client can see.

- `async me() -> CurrentUser | NetworkError` — GET /users/@me - the user behind the client's token.

## `wd_discord.entities.voice` — `wd-discord/src/wd_discord/entities/voice.py`
Voice states (https://docs.discord.com/developers/resources/voice#voice-state-object).

### `class VoiceState(Entity[VoiceStateModel])`
Which voice channel a user is in, bound to the client that can act on them and the channel.

- `@property user_id -> Snowflake` — The user this voice state is for.
- `@property guild_id -> Snowflake | None` — The guild this voice state is for; ``None`` for a voice state taken from GUILD_CREATE.
- `@property channel_id -> Snowflake | None` — The voice channel the user is in; ``None`` once they disconnected.
- `@property channel -> PartialChannel | None` — The voice channel the user is in; ``None`` once they disconnected.
- `@property member -> Member | PartialMember | None` — The member this voice state is for, in full when Discord sent it; ``None`` outside a guild.
