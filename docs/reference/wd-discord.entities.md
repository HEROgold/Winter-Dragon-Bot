<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_discord.entities` (wd-discord)
The high-level API: Discord objects bound to the client that acts on them, and the stores creating them.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_discord.entities` — `wd-discord/src/wd_discord/entities/__init__.py`

- exports: AnyInteraction, Application, AutocompleteInteraction, BaseChannel, BaseGlobalCommand, BaseGuild,
  BaseGuildCommand, BaseMember, BaseMessage, BaseRole, BaseUser, BoundEvent, Channel, ClientBound, CommandEntity,
  CommandInteraction, ComponentInteraction, CurrentApplication, CurrentUser, Emoji, Entitlement, Entity, EntityStore,
  GatewayGuild, GlobalCommand, GlobalCommandStore, Guild, GuildCommand, GuildCommandStore, Interaction, Invite, Member,
  Message, Partial, PartialChannel, PartialGlobalCommand, PartialGuild, PartialGuildCommand, PartialMember,
  PartialMessage, PartialRole, PartialUser, PermissionOverwrite, PermissionTarget, ReactionEmoji, Ready, Resolved, Role,
  Sticker, Store, Team, TeamMember, ThreadMember, UnknownInteraction, User, UserStore, VoiceState, WelcomeScreen,
  WelcomeScreenChannel, bind, event_entities

## `wd_discord.entities.application` — `wd-discord/src/wd_discord/entities/application.py`
The application behind the client's token (https://docs.discord.com/developers/resources/application).

### `class Application(Entity[ApplicationModel])`
An application, as Discord returned it.

- `@property id -> Snowflake` — The application's ID.
- `@property name -> str` — The application's name.
- `@property description -> str` — The application's description.
- `@property icon -> ImageHash | None` — The application's icon.
- `@property bot -> User | None` — The application's bot user.
- `@property owner -> User | None` — The user who owns the application; for a team-owned one, a placeholder user for the team.
- `@property team -> Team | None` — The team that owns the application, if a team does.
- `@property guild -> Guild | PartialGuild | None` — The guild linked to the application, such as its support server.
- `@property bot_public -> bool` — Whether anyone, not only the owner, may add the bot to a guild.
- `@property approximate_guild_count -> int | None` — Roughly how many guilds the application is in.
- `@property approximate_user_install_count -> int | None` — Roughly how many users installed the application.
- `@property tags -> list[str]` — Up to 5 tags describing the application.
- `@property install_params -> InstallParams | None` — The scopes and permissions of the application's default install link.
- `@property custom_install_url -> str | None` — The application's custom install link, if set.
- `@property terms_of_service_url -> str | None` — The application's terms of service.
- `@property privacy_policy_url -> str | None` — The application's privacy policy.

### `class Team(Entity[TeamModel])`
A developer team that owns applications (https://docs.discord.com/developers/topics/teams).

- `@property id -> Snowflake` — The team's ID.
- `@property name -> str` — The team's name.
- `@property icon -> ImageHash | None` — The team's icon.
- `@property members -> Generator[TeamMember]` — The team's members, invited ones included.
- `@property owner -> User | PartialUser` — The team's owner; in full when they are among its members.

### `class TeamMember(Entity[TeamMemberModel])`
A user on a developer team.

- `@property user -> User` — The member's user.
- `@property role -> str` — The member's role on the team: ``admin``, ``developer`` or ``read_only``.
- `@property membership_state -> MembershipState` — Whether the member accepted their invitation yet.

### `class CurrentApplication`
The client's own application: its data, its ID (which application-scoped routes need) and its commands.

- `async fetch() -> Application | NetworkError` — GET /applications/@me - the application object.
- `async id() -> Snowflake | NetworkError` — Return the application's ID, fetching and caching it when unknown.
- `guild_commands(guild: BaseGuild) -> GuildCommandStore` — Return the store of the application's commands registered in ``guild``.
- `async fetch_entitlements(*, user: BaseUser | None=None, guild: BaseGuild | None=None, exclude_ended: bool=False) -> Generator[Entitlement] | NetworkError` — GET /applications/{application_id}/entitlements - the application's entitlements, optionally for one owner.

## `wd_discord.entities.base` — `wd-discord/src/wd_discord/entities/base.py`
Bases of the high-level API: client-bound entities and the stores that create them.

- module names: logger
- `parse[M: DiscordModel](result: RequestResult, model: type[M]) -> M | NetworkError` — Return the failure in ``result``, or its JSON body validated as ``model``; an unreadable body is a failure.
- `parse_all[M: DiscordModel](result: RequestResult, model: type[M]) -> list[M] | NetworkError` — Return the failure in ``result``, or each item of its JSON array validated as ``model``.
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

- module names: DEFAULT_INVITE_MAX_AGE, MAX_MESSAGES_PER_PAGE
- `type PermissionTarget = BaseRole | BaseMember | BaseUser`

### `class BaseChannel(ClientBound)`
What can be done in a channel knowing only its ID: read, edit or delete it, send messages, set permissions.

- `@property mention -> str` — A clickable mention of the channel, as ``<#id>``.
- `async fetch() -> Channel | NetworkError` — GET /channels/{channel_id}.
- `message(message_id: SnowflakeLike) -> PartialMessage` — Return a handle on the message ``message_id`` in this channel, without fetching it.
- `async fetch_messages(*, before: BaseMessage | None=None, after: BaseMessage | None=None, around: BaseMessage | None=None, limit: int=MAX_MESSAGES_PER_PAGE) -> Generator[Message] | NetworkError` — GET /channels/{channel_id}/messages - one page of messages, newest first; needs READ_MESSAGE_HISTORY.
- `async send(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> Message | NetworkError` — POST /channels/{channel_id}/messages - send a message; DM channels included.
- `async delete_messages(messages: Iterable[BaseMessage], *, reason: AuditLogReason | str | None=None) -> NetworkError | None` — POST /channels/{channel_id}/messages/bulk-delete - delete 2 to 100 messages at once; needs MANAGE_MESSAGES.
- `async trigger_typing() -> NetworkError | None` — POST /channels/{channel_id}/typing - show the bot as typing for about 10 seconds, or until it sends.
- `async create_invite(*, max_age: int=DEFAULT_INVITE_MAX_AGE, max_uses: int=1, temporary: bool=False, unique: bool=True) -> Invite | NetworkError` — POST /channels/{channel_id}/invites - create an invite to this channel.
- `async fetch_invites() -> Generator[Invite] | NetworkError` — GET /channels/{channel_id}/invites - the channel's open invites; needs MANAGE_CHANNELS.
- `async edit(params: ChannelParams, *, reason: AuditLogReason | str | None=None) -> Channel | NetworkError` — PATCH /channels/{channel_id} - change the settings set in ``params``; needs MANAGE_CHANNELS.
- `async delete(*, reason: AuditLogReason | str | None=None) -> Channel | NetworkError` — DELETE /channels/{channel_id} - delete the channel, or close a DM; returns the deleted channel.
- `async set_permissions(target: PermissionTarget, *, allow: Permissions | None=None, deny: Permissions | None=None, reason: AuditLogReason | str | None=None) -> NetworkError | None` — PUT /channels/{channel_id}/permissions/{overwrite_id} - set ``target``'s overwrite on the channel.
- `async delete_permissions(target: PermissionTarget, *, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /channels/{channel_id}/permissions/{overwrite_id} - remove a role's or member's overwrite.
- `async join_thread() -> NetworkError | None` — PUT /channels/{channel_id}/thread-members/@me - add the bot to this thread.
- `async leave_thread() -> NetworkError | None` — DELETE /channels/{channel_id}/thread-members/@me - remove the bot from this thread.
- `async add_thread_member(user: BaseUser | BaseMember) -> NetworkError | None` — PUT /channels/{channel_id}/thread-members/{user_id} - add someone to this thread; needs SEND_MESSAGES.
- `async remove_thread_member(user: BaseUser | BaseMember) -> NetworkError | None` — DELETE /channels/{channel_id}/thread-members/{user_id} - remove someone from this thread; needs MANAGE_THREADS.

### `class Channel(Entity[ChannelModel], BaseChannel)`
A channel, as Discord returned it.

- `@property id -> Snowflake` — The channel's ID.
- `@property name -> str | None` — The channel's name; ``None`` for DM channels.
- `@property type -> ChannelType` — The kind of channel.
- `@property guild -> PartialGuild | None` — The guild the channel belongs to; ``None`` for DM channels.
- `@property parent -> PartialChannel | None` — The category a guild channel sits in, or the channel a thread was started in.
- `@property position -> int | None` — Where a guild channel sits in the channel list.
- `@property topic -> str | None` — The channel's topic, or a forum's guidelines.
- `@property nsfw -> bool` — Whether the channel is age-restricted.
- `@property last_message -> PartialMessage | None` — The latest message sent in the channel (or thread started, in a forum); it may have been deleted since.
- `@property bitrate -> int | None` — A voice channel's bitrate, in bits per second.
- `@property user_limit -> int | None` — How many users fit in a voice channel; ``0`` for no limit.
- `@property rate_limit_per_user -> int | None` — Slowmode: the seconds a member waits between messages; ``0`` when off.
- `@property rtc_region -> str | None` — A voice channel's region; ``None`` picks automatically.
- `@property video_quality_mode -> VideoQualityMode | None` — A voice channel's camera video quality.
- `@property recipients -> Generator[User]` — The other users in a DM or group DM.
- `@property icon -> ImageHash | None` — A group DM's icon.
- `@property owner -> PartialUser | None` — Who created a group DM or thread.
- `@property overwrites -> Generator[PermissionOverwrite]` — The channel's permission overwrites; empty outside a guild.
- `@property thread_metadata -> ThreadMetadata | None` — A thread's archive and lock state.
- `@property thread_member -> ThreadMember | None` — The bot's membership of this thread, when it joined it.
- `@property message_count -> int | None` — How many messages a thread holds, deleted ones excluded.
- `@property member_count -> int | None` — Roughly how many users are in a thread; stops counting at 50.
- `@property default_auto_archive_duration -> int | None` — The minutes of inactivity before a new thread is archived.
- `@property available_tags -> list[ForumTag]` — The tags a forum or media channel offers its posts.
- `@property applied_tags -> list[Snowflake]` — The IDs of the parent forum's tags applied to this post.
- `@property permissions -> Permissions | None` — The invoking user's permissions in the channel, overwrites included.
- `@property app_permissions -> Permissions | None` — The bot's permissions in the channel, overwrites included.

### `class PartialChannel(BaseChannel, Partial[Channel])`
A channel known only by ID.

### `@dataclass class PermissionOverwrite(Entity[PermissionOverwriteModel])`
One role's or member's permission overwrite on a guild channel.

- fields: channel_id: Snowflake, guild_id: Snowflake
- `@property id -> Snowflake` — The ID of the role or member the overwrite applies to.
- `@property type -> OverwriteType` — Whether the overwrite applies to a role or a member.
- `@property target -> PartialRole | PartialMember` — The role or member the overwrite applies to.
- `@property channel -> PartialChannel` — The channel the overwrite is set on.
- `@property allow -> Permissions` — The permissions the overwrite grants.
- `@property deny -> Permissions` — The permissions the overwrite takes away.
- `async delete(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /channels/{channel_id}/permissions/{overwrite_id}; needs MANAGE_ROLES.

### `@dataclass class ThreadMember(Entity[ThreadMemberModel])`
A user's membership of a thread.

- fields: thread_id: Snowflake
- `@property thread -> PartialChannel` — The thread the membership is for.
- `@property user -> PartialUser | None` — The member of the thread; Discord leaves it out of some payloads.
- `@property joined_at -> datetime` — When the user last joined the thread.
- `@property flags -> int` — The user's notification settings for the thread.

## `wd_discord.entities.command` — `wd-discord/src/wd_discord/entities/command.py`
Application commands (https://docs.discord.com/developers/interactions/application-commands).

### `class BaseGlobalCommand(ClientBound)`
What can be done to a global command knowing only its ID: read it again, edit it, delete it.

- `async fetch() -> GlobalCommand | NetworkError` — GET /applications/{application_id}/commands/{command_id}.
- `async edit(params: ApplicationCommandParams) -> GlobalCommand | NetworkError` — PATCH /applications/{application_id}/commands/{command_id} - replace the command's definition.
- `async delete() -> NetworkError | None` — DELETE /applications/{application_id}/commands/{command_id}.

### `class CommandEntity(Entity[ApplicationCommand])`
The fields every registered command shares, global or guild.

- `@property id -> Snowflake` — The command's ID.
- `@property name -> str` — The command's name.
- `@property description -> str` — The command's description; empty for user and message commands.
- `@property type -> ApplicationCommandType` — Whether it's a slash, user or message command.
- `@property options -> list[ApplicationCommandOption]` — The command's options, or its subcommands.
- `@property default_member_permissions -> Permissions | None` — The permissions a member needs to see the command by default; ``None`` for everyone.
- `@property nsfw -> bool` — Whether the command only shows in age-restricted channels.
- `@property contexts -> list[InteractionContextType] | None` — Where the command can be used: guilds, the bot's DM, other DMs.
- `@property version -> Snowflake` — Discord's auto-incrementing version of the definition; changes on every edit.
- `@property mention -> str` — A clickable mention of the command, as ``</name:id>``.
- `to_params() -> ApplicationCommandParams` — Return the definition the command was registered with, to compare or re-register it.

### `class GlobalCommand(CommandEntity, BaseGlobalCommand)`
A registered global command, as Discord returned it.

### `class PartialGlobalCommand(BaseGlobalCommand, Partial[GlobalCommand])`
A global command known only by ID, e.g. one stored from an earlier sync.

### `@dataclass class GlobalCommandStore(EntityStore[PartialGlobalCommand])`
The application's global commands: register, fetch and list them.

- `async path(command_id: SnowflakeLike | None=None) -> Template | NetworkError` — Return the global-commands route, or one command's, or the failure looking up the application ID.
- `async create(params: ApplicationCommandParams) -> GlobalCommand | NetworkError` — POST /applications/{application_id}/commands - register a new global command.
- `async fetch_all() -> Generator[GlobalCommand] | NetworkError` — GET /applications/{application_id}/commands - every registered global command.
- `async overwrite(params: Iterable[ApplicationCommandParams]) -> Generator[GlobalCommand] | NetworkError` — PUT /applications/{application_id}/commands - replace every global command with ``params``.

### `class BaseGuildCommand(ClientBound)`
What can be done to a guild command knowing only its guild and ID: read it again, edit it, delete it.

- `@property guild -> PartialGuild` — The guild the command is registered in.
- `async fetch() -> GuildCommand | NetworkError` — GET /applications/{application_id}/guilds/{guild_id}/commands/{command_id}.
- `async edit(params: ApplicationCommandParams) -> GuildCommand | NetworkError` — PATCH /applications/{application_id}/guilds/{guild_id}/commands/{command_id} - replace the definition.
- `async delete() -> NetworkError | None` — DELETE /applications/{application_id}/guilds/{guild_id}/commands/{command_id}.

### `class GuildCommand(CommandEntity, BaseGuildCommand)`
A command registered in one guild, as Discord returned it.

- `@property guild_id -> Snowflake` — The guild the command is registered in.

### `@dataclass class PartialGuildCommand(BaseGuildCommand, Partial[GuildCommand])`
A guild command known only by guild and ID.

- fields: guild_id: Snowflake

### `@dataclass class GuildCommandStore(Store)`
One guild's commands for the application: list them, or replace them all.

- fields: guild_id: Snowflake
- `async path() -> Template | NetworkError` — Return the guild-commands route, or the failure looking up the application ID.
- `partial(command_id: SnowflakeLike) -> PartialGuildCommand` — Return a handle on the guild command ``command_id``, without fetching it.
- `async fetch(command_id: SnowflakeLike) -> GuildCommand | NetworkError` — GET /applications/{application_id}/guilds/{guild_id}/commands/{command_id}.
- `async create(params: ApplicationCommandParams) -> GuildCommand | NetworkError` — POST /applications/{application_id}/guilds/{guild_id}/commands - register a command in the guild.
- `async fetch_all() -> Generator[GuildCommand] | NetworkError` — GET /applications/{application_id}/guilds/{guild_id}/commands - every command registered in the guild.
- `async overwrite(params: Iterable[ApplicationCommandParams]) -> Generator[GuildCommand] | NetworkError` — PUT /applications/{application_id}/guilds/{guild_id}/commands - replace the guild's commands with ``params``.

## `wd_discord.entities.emoji` — `wd-discord/src/wd_discord/entities/emoji.py`
Guild emojis and stickers (https://docs.discord.com/developers/resources/emoji, .../resources/sticker).

### `@dataclass class Emoji(Entity[EmojiModel])`
A guild's custom emoji, as Discord returned it.

- fields: guild_id: Snowflake
- `@property id -> Snowflake | None` — The emoji's ID; ``None`` only for a unicode emoji in a reaction.
- `@property name -> str | None` — The emoji's name.
- `@property guild -> PartialGuild` — The guild the emoji belongs to.
- `@property roles -> Generator[PartialRole]` — The roles allowed to use the emoji; empty when everyone may.
- `@property user -> User | None` — Who uploaded the emoji; only sent with MANAGE_GUILD_EXPRESSIONS.
- `@property animated -> bool` — Whether the emoji is animated.
- `@property available -> bool` — Whether the emoji can be used; ``False`` after the guild lost the boosts it needs.
- `@property mention -> str` — The emoji as it's written in a message: ``<:name:id>``, or ``<a:name:id>`` when animated.
- `async fetch() -> Emoji | NetworkError` — GET /guilds/{guild_id}/emojis/{emoji_id}.
- `async delete(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /guilds/{guild_id}/emojis/{emoji_id}; needs MANAGE_GUILD_EXPRESSIONS.

### `class Sticker(Entity[StickerModel])`
A sticker, as Discord returned it: a guild's own, or a standard one from a pack.

- `@property id -> Snowflake` — The sticker's ID.
- `@property name -> str` — The sticker's name.
- `@property description -> str | None` — The sticker's description.
- `@property tags -> str` — The autocomplete tags for the sticker.
- `@property type -> StickerType` — Whether the sticker is a standard or a guild sticker.
- `@property format_type -> StickerFormatType` — The sticker's image format.
- `@property available -> bool` — Whether a guild sticker can be used; ``False`` after the guild lost the boosts it needs.
- `@property guild -> PartialGuild | None` — The guild that owns the sticker; ``None`` for a standard sticker.
- `@property user -> User | None` — Who uploaded a guild sticker; only sent with MANAGE_GUILD_EXPRESSIONS.
- `async fetch() -> Sticker | NetworkError` — GET /stickers/{sticker_id}.
- `async delete(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /guilds/{guild_id}/stickers/{sticker_id} - delete a guild sticker; needs MANAGE_GUILD_EXPRESSIONS.

## `wd_discord.entities.entitlement` — `wd-discord/src/wd_discord/entities/entitlement.py`
Entitlements (https://docs.discord.com/developers/resources/entitlement).

### `class Entitlement(Entity[EntitlementModel])`
A user's or guild's access to one of the application's SKUs.

- `@property id -> Snowflake` — The entitlement's ID.
- `@property sku_id -> Snowflake` — The ID of the SKU it grants.
- `@property type -> EntitlementType` — How the entitlement was obtained.
- `@property user -> PartialUser | None` — The user granted access; ``None`` for a guild's entitlement.
- `@property guild -> PartialGuild | None` — The guild granted access; ``None`` for a user's entitlement.
- `@property deleted -> bool` — Whether the entitlement was deleted.
- `@property consumed -> bool` — Whether a consumable entitlement was used up.
- `@property starts_at -> datetime | None` — When the entitlement starts being valid.
- `@property ends_at -> datetime | None` — When the entitlement stops being valid; ``None`` when it doesn't expire.
- `async consume() -> NetworkError | None` — POST /applications/{application_id}/entitlements/{entitlement_id}/consume - mark a consumable as used.
- `async delete() -> NetworkError | None` — DELETE /applications/{application_id}/entitlements/{entitlement_id} - remove a test entitlement.

## `wd_discord.entities.events` — `wd-discord/src/wd_discord/entities/events.py`
Gateway dispatch events bound to the client that received them.

- `type BoundEvent = AnyInteraction | Message | GatewayGuild | Ready | VoiceState`
- `bind(client: Client, model: DiscordModel) -> BoundEvent | DiscordModel` — Wrap a parsed dispatch ``model`` in the entity bound to ``client``, or return it as is if it has none.
- `event_entities() -> Mapping[EventName, type | TypeAliasType]` — Return the entity (or union of entities) :func:`bind` returns for each event; the source of ``listener.pyi``.

## `wd_discord.entities.guild` — `wd-discord/src/wd_discord/entities/guild.py`
Guilds (https://docs.discord.com/developers/resources/guild).

- module names: MAX_MEMBERS_PER_PAGE

### `class BaseGuild(ClientBound)`
What can be done to a guild knowing only its ID: read it, its channels, members, roles and expressions.

- `async fetch(*, with_counts: bool=False) -> Guild | NetworkError` — GET /guilds/{guild_id}; ``with_counts`` fills in the approximate member and online counts.
- `channel(channel_id: SnowflakeLike) -> PartialChannel` — Return a handle on the channel ``channel_id``, without fetching it.
- `async fetch_channels() -> Generator[Channel] | NetworkError` — GET /guilds/{guild_id}/channels - the guild's channels, threads excluded.
- `async create_channel(params: GuildChannelParams, *, reason: AuditLogReason | str | None=None) -> Channel | NetworkError` — POST /guilds/{guild_id}/channels - create a channel or category; needs MANAGE_CHANNELS.
- `member(user_id: SnowflakeLike) -> PartialMember` — Return a handle on the member ``user_id`` of this guild, without fetching them.
- `async fetch_members(*, after: BaseMember | BaseUser | None=None, limit: int=MAX_MEMBERS_PER_PAGE) -> Generator[Member] | NetworkError` — GET /guilds/{guild_id}/members - one page of members, by user ID, after the member ``after``.
- `async search_members(query: str, *, limit: int=1) -> Generator[Member] | NetworkError` — GET /guilds/{guild_id}/members/search - the members whose username or nickname starts with ``query``.
- `role(role_id: SnowflakeLike) -> PartialRole` — Return a handle on the role ``role_id`` of this guild, without fetching it.
- `async fetch_roles() -> Generator[Role] | NetworkError` — GET /guilds/{guild_id}/roles - every role of the guild.
- `async fetch_emojis() -> Generator[Emoji] | NetworkError` — GET /guilds/{guild_id}/emojis - the guild's custom emojis.
- `async fetch_emoji(emoji_id: SnowflakeLike) -> Emoji | NetworkError` — GET /guilds/{guild_id}/emojis/{emoji_id}.
- `async fetch_stickers() -> Generator[Sticker] | NetworkError` — GET /guilds/{guild_id}/stickers - the guild's own stickers.
- `async fetch_invites() -> Generator[Invite] | NetworkError` — GET /guilds/{guild_id}/invites - every open invite to the guild; needs MANAGE_GUILD.
- `async fetch_voice_state(member: BaseMember | BaseUser | None=None) -> VoiceState | NetworkError` — GET /guilds/{guild_id}/voice-states/{user_id} - ``member``'s voice state here, or the bot's without one.
- `async fetch_welcome_screen() -> WelcomeScreen | NetworkError` — GET /guilds/{guild_id}/welcome-screen; needs MANAGE_GUILD unless the screen is enabled.
- `async leave() -> NetworkError | None` — DELETE /users/@me/guilds/{guild_id} - remove the bot from the guild; fails for a guild it owns.

### `class Guild(Entity[GuildModel], BaseGuild)`
A guild, as Discord returned it.

- `@property id -> Snowflake` — The guild's ID.
- `@property name -> str` — The guild's name.
- `@property description -> str | None` — The guild's description, for a community guild.
- `@property icon -> ImageHash | None` — The guild's icon.
- `@property splash -> ImageHash | None` — The guild's invite background.
- `@property banner -> ImageHash | None` — The guild's banner.
- `@property owner -> Member | PartialMember` — The guild's owner.
- `@property afk_channel -> Channel | PartialChannel | None` — The voice channel idle members are moved to, if the guild has one.
- `@property afk_timeout -> int` — The seconds a member idles in voice before they're moved to the AFK channel.
- `@property widget_channel -> Channel | PartialChannel | None` — The channel the guild's widget invites to, if set.
- `@property system_channel -> Channel | PartialChannel | None` — The channel Discord posts join and boost messages in, if set.
- `@property rules_channel -> Channel | PartialChannel | None` — A community guild's rules channel.
- `@property public_updates_channel -> Channel | PartialChannel | None` — The channel a community guild receives notices from Discord in.
- `@property safety_alerts_channel -> Channel | PartialChannel | None` — The channel a community guild receives safety alerts from Discord in.
- `@property roles -> Generator[Role]` — The guild's roles, ``@everyone`` included.
- `@property default_role -> Role | PartialRole` — The ``@everyone`` role, which shares the guild's ID.
- `get_role(role_id: SnowflakeLike) -> Role | None` — Return the role ``role_id`` from the guild's data, without a request; ``None`` if it isn't one of them.
- `get_member(user_id: SnowflakeLike) -> Member | None` — Return the member ``user_id`` from the guild's data, without a request; a fetched guild has none.
- `get_channel(channel_id: SnowflakeLike) -> Channel | None` — Return the channel ``channel_id`` from the guild's data, without a request; a fetched guild has none.
- `@property emojis -> Generator[Emoji]` — The guild's custom emojis.
- `@property stickers -> Generator[Sticker]` — The guild's own stickers.
- `@property features -> list[str]` — The guild's enabled features, such as ``COMMUNITY``.
- `@property verification_level -> VerificationLevel` — What a member must have done before they may talk.
- `@property mfa_level -> MFALevel` — Whether moderators need two-factor authentication.
- `@property nsfw_level -> NSFWLevel` — The guild's age-restriction level.
- `@property premium_tier -> PremiumTier` — The guild's boost level.
- `@property premium_subscription_count -> int | None` — How many boosts the guild has.
- `@property preferred_locale -> str` — The language of a community guild, such as ``en-US``.
- `@property vanity_url_code -> str | None` — The guild's vanity invite code, if it has one.
- `@property max_members -> int | None` — The most members the guild can hold.
- `@property approximate_member_count -> int | None` — Roughly how many members the guild has; only from :meth:`fetch` with ``with_counts``.
- `@property approximate_presence_count -> int | None` — Roughly how many members are online; only from :meth:`fetch` with ``with_counts``.
- `@property welcome_screen -> WelcomeScreen | None` — A community guild's welcome screen, when Discord sent it along.

### `class GatewayGuild(Guild)`
A guild as GUILD_CREATE sent it: with its channels, threads, members and voice states.

- `@property channels -> Generator[Channel]` — The guild's channels, threads excluded.
- `@property threads -> Generator[Channel]` — The active threads the bot can see.
- `@property members -> Generator[Member]` — The members Discord sent along; see the class docstring for which.
- `@property voice_states -> Generator[VoiceState]` — Who is in which of the guild's voice channels.
- `@property member_count -> int | None` — How many members the guild has.
- `@property large -> bool` — Whether the guild is past the gateway's large threshold, so ``members`` is incomplete.
- `@property joined_at -> str | None` — When the bot joined the guild, as an ISO 8601 timestamp.
- `get_member(user_id: SnowflakeLike) -> Member | None` — Return the member ``user_id`` if Discord sent them along, without a request.
- `get_channel(channel_id: SnowflakeLike) -> Channel | None` — Return the channel or thread ``channel_id`` of the guild, without a request.

### `class PartialGuild(BaseGuild, Partial[Guild])`
A guild known only by ID.

### `@dataclass class WelcomeScreen(Entity[WelcomeScreenModel])`
The screen a community guild shows new members: a description and up to 5 channels to start in.

- fields: guild_id: Snowflake
- `@property guild -> PartialGuild` — The guild the welcome screen belongs to.
- `@property description -> str | None` — The guild description shown on the screen.
- `@property channels -> Generator[WelcomeScreenChannel]` — The channels the screen suggests, in order.

### `class WelcomeScreenChannel(Entity[WelcomeScreenChannelModel])`
One channel a welcome screen suggests.

- `@property channel -> PartialChannel` — The suggested channel.
- `@property description -> str` — What the screen says about the channel.
- `@property emoji -> PartialEmoji | None` — The emoji shown next to the channel, if any.

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
- `@property member -> Member | None` — The invoking guild member, when invoked in a guild.
- `@property guild -> PartialGuild | None` — The guild the interaction was sent from, if any.
- `@property channel -> Channel | PartialChannel | None` — The channel the interaction was sent from, in full when Discord sent it along (it usually does).
- `@property entitlements -> Generator[Entitlement]` — The invoking user's and guild's entitlements to the application's SKUs.
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
- `@property resolved -> Resolved | None` — Full objects for the users, roles and channels the option values name.

### `class ComponentInteraction(Interaction[ComponentInteractionModel])`
Someone clicked a button or chose from a select menu.

- `@property custom_id -> str` — The ``custom_id`` of the component that was used.
- `@property component_type -> ComponentType` — The kind of component that was used.
- `@property values -> list[str]` — The chosen values of a select menu; empty for buttons.
- `@property message -> Message` — The message the component is attached to.
- `async update(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> NetworkError | None` — Edit the component's message as the initial response.
- `async defer_update() -> NetworkError | None` — Acknowledge now, without a loading state, and edit the component's message later; no-op once answered.

### `class AutocompleteInteraction(Interaction[AutocompleteInteractionModel])`
Someone is typing a value for an autocomplete option.

- `@property command_name -> str` — The name of the command being filled in.
- `@property options -> list[InteractionDataOption]` — The option values typed so far; the one being typed has ``focused`` set.
- `@property resolved -> Resolved | None` — Full objects for the users, roles and channels the option values typed so far name.
- `async suggest(choices: Sequence[ApplicationCommandOptionChoice]) -> NetworkError | None` — Offer ``choices`` (at most 25) for the focused option.

### `class UnknownInteraction(Interaction[InteractionModel])`
An interaction type without its own class yet (PING, MODAL_SUBMIT).

## `wd_discord.entities.invite` — `wd-discord/src/wd_discord/entities/invite.py`
Invites (https://docs.discord.com/developers/resources/invite).

### `class Invite(Entity[InviteModel])`
An invite to a guild channel, as Discord returned it.

- `@property code -> str` — The invite's code, the last part of its URL.
- `@property url -> str` — The invite's shareable URL.
- `@property guild -> PartialGuild | None` — The guild the invite is for; Discord sends only a summary of it.
- `@property channel -> PartialChannel | None` — The channel the invite opens; Discord sends only a summary of it.
- `@property inviter -> User | None` — Who created the invite.
- `@property uses -> int | None` — How often the invite was used; only sent to whoever may manage it.
- `@property max_uses -> int | None` — How often the invite may be used; ``0`` for unlimited.
- `@property max_age -> int | None` — The seconds the invite stays valid after creation; ``0`` for forever.
- `@property temporary -> bool` — Whether members who join through the invite are removed again when they disconnect without a role.
- `async fetch() -> Invite | NetworkError` — GET /invites/{invite_code}.
- `async delete(*, reason: AuditLogReason | str | None=None) -> Invite | NetworkError` — DELETE /invites/{invite_code} - revoke the invite; needs MANAGE_CHANNELS on its channel, or MANAGE_GUILD.

## `wd_discord.entities.member` — `wd-discord/src/wd_discord/entities/member.py`
Guild members (https://docs.discord.com/developers/resources/guild#guild-member-object).

### `class BaseMember(ClientBound)`
What can be done to a guild member knowing only their guild and user ID: read, edit, moderate them.

- `@property mention -> str` — A clickable mention of the member, as ``<@id>``.
- `@property guild -> PartialGuild` — The guild the member is in.
- `async fetch() -> Member | NetworkError` — GET /guilds/{guild_id}/members/{user_id}.
- `async move_to(channel: BaseChannel | None, *, reason: AuditLogReason | str | None=None) -> Member | NetworkError` — PATCH /guilds/{guild_id}/members/{user_id} - move the member to the voice ``channel``.
- `async set_nick(nick: str | None, *, reason: AuditLogReason | str | None=None) -> Member | NetworkError` — PATCH /guilds/{guild_id}/members/{user_id} - set the member's nickname, or clear it with ``None``.
- `async timeout(until: datetime | None, *, reason: AuditLogReason | str | None=None) -> Member | NetworkError` — PATCH /guilds/{guild_id}/members/{user_id} - time the member out until ``until`` (at most 28 days ahead).
- `async add_role(role: BaseRole, *, reason: AuditLogReason | str | None=None) -> NetworkError | None` — PUT /guilds/{guild_id}/members/{user_id}/roles/{role_id}; needs MANAGE_ROLES and a higher role.
- `async remove_role(role: BaseRole, *, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id}; needs MANAGE_ROLES and a higher role.
- `async kick(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /guilds/{guild_id}/members/{user_id} - remove the member from the guild; needs KICK_MEMBERS.
- `async ban(*, delete_message_seconds: int=0, reason: AuditLogReason | str | None=None) -> NetworkError | None` — PUT /guilds/{guild_id}/bans/{user_id} - ban the member; needs BAN_MEMBERS.
- `async unban(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /guilds/{guild_id}/bans/{user_id} - lift the ban on this user; needs BAN_MEMBERS.

### `@dataclass class Member(Entity[GuildMember], BaseMember)`
A guild member, as Discord returned them; always with their user.

- fields: guild_id: Snowflake
- `@property id -> Snowflake` — The member's user ID.
- `@property user -> User` — The user behind the membership.
- `@property bot -> bool` — Whether the member is a bot account.
- `@property nick -> str | None` — The member's guild nickname, if set.
- `@property display_name -> str` — The member's guild nickname, else their global display name, else their username.
- `@property avatar -> ImageHash | None` — The member's guild-specific avatar, if set.
- `@property roles -> Generator[PartialRole]` — The member's roles, ``@everyone`` excluded.
- `@property joined_at -> datetime | None` — When the member joined the guild; ``None`` for a guest in a voice channel.
- `@property premium_since -> datetime | None` — When the member started boosting the guild; ``None`` when not boosting.
- `@property deaf -> bool` — Whether the member is deafened in voice channels.
- `@property mute -> bool` — Whether the member is muted in voice channels.
- `@property pending -> bool` — Whether the member hasn't passed the guild's membership screening yet.
- `@property flags -> GuildMemberFlags` — The member's guild member flags.
- `@property permissions -> Permissions | None` — The member's permissions in the interaction's channel; only known for an interaction's member.
- `@property communication_disabled_until -> datetime | None` — When the member's timeout ends; ``None`` (or a past time) when not timed out.

### `@dataclass class PartialMember(BaseMember, Partial[Member])`
A guild member known only by guild and user ID.

- fields: guild_id: Snowflake
- `@property user -> PartialUser` — The user behind the membership.

## `wd_discord.entities.message` — `wd-discord/src/wd_discord/entities/message.py`
Messages (https://docs.discord.com/developers/resources/message).

- `type ReactionEmoji = str | Emoji | PartialEmoji`
- `reaction_name(emoji: ReactionEmoji) -> str` — Return ``emoji`` as Discord's reaction routes name it: the unicode character, or ``name:id``.

### `class BaseMessage(ClientBound)`
What can be done to a message knowing only its channel and ID: read, edit, delete, react to and pin it.

- `@property channel -> PartialChannel` — The channel the message was sent in.
- `@property jump_url -> str` — A link that opens the message; works in DMs and guilds alike.
- `async fetch() -> Message | NetworkError` — GET /channels/{channel_id}/messages/{message_id}; needs READ_MESSAGE_HISTORY in a guild.
- `async edit(content: str | None=None, *, embeds: Sequence[Embed] | None=None, components: Sequence[ActionRow] | None=None) -> Message | NetworkError` — PATCH /channels/{channel_id}/messages/{message_id} - edit a message the bot sent.
- `async delete(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /channels/{channel_id}/messages/{message_id}; someone else's message needs MANAGE_MESSAGES.
- `async add_reaction(emoji: ReactionEmoji) -> NetworkError | None` — PUT /channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me - react as the bot.
- `async remove_reaction(emoji: ReactionEmoji, user: BaseUser | BaseMember | None=None) -> NetworkError | None` — DELETE .../reactions/{emoji}/{user_id} - take back the bot's reaction, or ``user``'s (needs MANAGE_MESSAGES).
- `async clear_reactions(emoji: ReactionEmoji | None=None) -> NetworkError | None` — DELETE .../reactions[/{emoji}] - remove every reaction, or every one with ``emoji``; needs MANAGE_MESSAGES.
- `async pin(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — PUT /channels/{channel_id}/messages/pins/{message_id}; needs PIN_MESSAGES.
- `async unpin(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /channels/{channel_id}/messages/pins/{message_id}; needs PIN_MESSAGES.

### `class Message(Entity[MessageModel], BaseMessage)`
A message, as Discord returned or dispatched it.

- `@property id -> Snowflake` — The message's ID.
- `@property channel_id -> Snowflake` — The channel the message was sent in.
- `@property content -> str` — The message's text; empty without the MESSAGE_CONTENT intent, unless the bot is mentioned.
- `@property author -> User` — Who sent the message.
- `@property guild -> PartialGuild | None` — The guild the message was sent in; ``None`` in a DM or when Discord left it out.
- `@property timestamp -> str` — When the message was sent, as an ISO 8601 timestamp.
- `@property edited_timestamp -> str | None` — When the message was last edited, as an ISO 8601 timestamp; ``None`` if never.
- `@property tts -> bool` — Whether the message was sent as text-to-speech.
- `@property mention_everyone -> bool` — Whether the message mentions ``@everyone``.
- `@property jump_url -> str` — A link that opens the message.

### `@dataclass class PartialMessage(BaseMessage, Partial[Message])`
A message known only by channel and ID.

- fields: channel_id: Snowflake

## `wd_discord.entities.ready` — `wd-discord/src/wd_discord/entities/ready.py`
The READY a shard receives once it has connected (https://docs.discord.com/developers/events/gateway-events#ready).

### `class Ready(Entity[ReadyModel])`
A shard finished connecting: who the bot is, and which guilds will follow as GUILD_CREATE.

- `@property user -> CurrentUser` — The user behind the client's token.
- `@property guilds -> Generator[PartialGuild]` — The guilds this shard serves; each one arrives in full later as a GUILD_CREATE.
- `@property session_id -> str` — The session ID, for resuming the connection.
- `@property shard -> tuple[int, int] | None` — The ``(shard_id, num_shards)`` of the shard that received it, when sharding.
- `@property application_id -> str | None` — The ID of the bot's application.

## `wd_discord.entities.resolved` — `wd-discord/src/wd_discord/entities/resolved.py`
The objects an interaction's options name, as Discord sent them along.

### `@dataclass class Resolved(Entity[ResolvedData])`
Full objects for the user, role and channel IDs an interaction's option values hold, keyed by ID.

- fields: guild_id: Snowflake | None
- `@property users -> dict[Snowflake, User]` — The users option values name.
- `@property roles -> dict[Snowflake, Role]` — The roles option values name; empty outside a guild.
- `@property channels -> dict[Snowflake, Channel]` — The channels option values name, with the invoking user's ``permissions`` in each.
- `user(user_id: SnowflakeLike) -> User | None` — Return the user ``user_id`` names, if Discord sent them along.
- `role(role_id: SnowflakeLike) -> Role | None` — Return the role ``role_id`` names, if Discord sent it along.
- `channel(channel_id: SnowflakeLike) -> Channel | None` — Return the channel ``channel_id`` names, if Discord sent it along.

## `wd_discord.entities.role` — `wd-discord/src/wd_discord/entities/role.py`
Roles (https://docs.discord.com/developers/topics/permissions#role-object).

### `class BaseRole(ClientBound)`
What can be done to a role knowing only its guild and ID: read it, delete it, mention it.

- `@property guild -> PartialGuild` — The guild the role belongs to.
- `@property mention -> str` — A clickable mention of the role, as ``<@&id>``; ``@everyone`` for the guild's default role.
- `@property is_default -> bool` — Whether this is the guild's ``@everyone`` role, which shares the guild's ID.
- `async fetch() -> Role | NetworkError` — GET /guilds/{guild_id}/roles/{role_id}.
- `async delete(*, reason: AuditLogReason | str | None=None) -> NetworkError | None` — DELETE /guilds/{guild_id}/roles/{role_id}; needs MANAGE_ROLES.

### `@dataclass class Role(Entity[RoleModel], BaseRole)`
A role, as Discord returned it.

- fields: guild_id: Snowflake
- `@property id -> Snowflake` — The role's ID.
- `@property name -> str` — The role's name.
- `@property color -> int` — The role's color as an RGB integer; ``0`` for no color.
- `@property colors -> RoleColors | None` — The role's gradient colors, when it has them.
- `@property hoist -> bool` — Whether members with this role show separately in the member list.
- `@property icon -> ImageHash | None` — The role's icon, if it has one.
- `@property unicode_emoji -> str | None` — The role's unicode emoji, if it has one.
- `@property position -> int` — Where the role sits in the guild's role list; a higher role outranks a lower one.
- `@property permissions -> Permissions` — The permissions the role grants.
- `@property managed -> bool` — Whether an integration (a bot, boosting, a subscription) manages the role.
- `@property mentionable -> bool` — Whether anyone may mention the role.
- `@property tags -> RoleTags | None` — What manages the role, for a managed role.

### `@dataclass class PartialRole(BaseRole, Partial[Role])`
A role known only by guild and ID.

- fields: guild_id: Snowflake

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
Which voice channel a user is in, and how they're muted, bound to the client that can act on them.

- `@property user -> User | PartialUser` — The user this voice state is for; in full when Discord sent their member along.
- `@property member -> Member | PartialMember | None` — The member this voice state is for, in full when Discord sent it; ``None`` outside a guild.
- `@property guild -> PartialGuild | None` — The guild this voice state is for; ``None`` outside a guild.
- `@property channel -> PartialChannel | None` — The voice channel the user is in; ``None`` once they disconnected.
- `@property session_id -> str` — The voice session's ID.
- `@property deaf -> bool` — Whether the guild deafened the user.
- `@property mute -> bool` — Whether the guild muted the user.
- `@property self_deaf -> bool` — Whether the user deafened themselves.
- `@property self_mute -> bool` — Whether the user muted themselves.
- `@property self_stream -> bool` — Whether the user is streaming with Go Live.
- `@property self_video -> bool` — Whether the user's camera is on.
- `@property suppress -> bool` — Whether the user may not speak, as in a stage channel's audience.
- `@property request_to_speak_timestamp -> datetime | None` — When the user raised their hand in a stage channel.
