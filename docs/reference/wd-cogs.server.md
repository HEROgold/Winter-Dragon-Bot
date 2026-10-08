<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_cogs.server` (wd-cogs)
Package for server cogs.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_cogs.server` — `wd-cogs/src/wd_cogs/server/__init__.py`

- exports: Announce, AutoAssign, Purge, Stats, SyncedBans, Welcome

## `wd_cogs.server.announcement` — `wd-cogs/src/wd_cogs/server/announcement.py`
A cog for announcing messages.

### `class Announce(Cog, auto_load=True)`
A cog for announcing messages about the bot to all servers.

- attributes: mention_all
- `@app_commands.command @app_commands.checks.has_permissions async announce(interaction: discord.Interaction, message: str) -> None` — Send an announcement to all servers.

## `wd_cogs.server.audit_event_listener` — `wd-cogs/src/wd_cogs/server/audit_event_listener.py`
Module for handling audit log events.

### `class EventListener(Cog, auto_load=True)`
Event listener for audit log entries.

- `@Cog.listener async on_audit_log_entry_create(entry: AuditLogEntry) -> None` — Handle the audit log entry.

## `wd_cogs.server.auto_assign` — `wd-cogs/src/wd_cogs/server/auto_assign.py`
Cog for automatically assigning roles to new members.

### `class AutoAssign(GroupCog, auto_load=True)`
Cog for automatically assigning roles to new members.

- attributes: auto_assign_reason
- `@app_commands.command async slash_assign_show(interaction: discord.Interaction) -> None` — Show the current auto assign role.
- `@app_commands.command async slash_assign_add(interaction: discord.Interaction, role: discord.Role) -> None` — Add a role to the list of roles to be assigned to new members.
- `@app_commands.command async slash_assign_remove(interaction: discord.Interaction, role: discord.Role | None=None) -> None` — Remove a role from the list of roles to be assigned to new members.
- `async remove_specified_role(interaction: discord.Interaction, role: discord.Role) -> None` — Remove a specific role from the list of roles to be assigned to new members.
- `async remove_all_roles(interaction: discord.Interaction) -> None` — Remove all roles from the list of roles to be assigned to new members.
- `@Cog.listener async on_member_join(member: discord.Member) -> None` — Automatically assign roles to new members.

## `wd_cogs.server.autochannel` — `wd-cogs/src/wd_cogs/server/autochannel.py`
Module containing the automatic channel cog.

### `@app_commands.guild_only class AutomaticChannels(GroupCog, auto_load=True)`
Automatic channels for users to create their own (temporary) channels.

- attributes: create_reason
- `@Cog.listener async on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None` — When a user joins a voice channel, create a new channel for them.
- `async create_user_channel(member: discord.Member, after: discord.VoiceState, guild: discord.Guild) -> None` — Create a automatic channel for a user.
- `get_final_settings(member: discord.Member, setting: ACS | None, guild_setting: ACS | None) -> tuple[str | None, int]` — Get the final settings for the channel. returning the most restrictive settings where possible.
- `@app_commands.checks.has_permissions @app_commands.command async slash_setup(interaction: discord.Interaction, category_name: str, voice_channel_name: str) -> None` — Set up the AutoChannel system for this guild.
- `@app_commands.checks.has_permissions @app_commands.command async slash_mark(interaction: discord.Interaction, channel: discord.VoiceChannel | None=None) -> None` — Mark the current channel or a given channel to be the main AutoChannel.
- `@app_commands.checks.has_permissions @app_commands.command async slash_set_guild_limit(interaction: discord.Interaction, limit: int) -> None` — Set a limit for AutoChannels.
- `@app_commands.command async slash_limit(interaction: discord.Interaction, limit: int) -> None` — Set a limit for your channel.
- `@slash_setup.error async info_error(interaction: discord.Interaction, error: Exception) -> None` — Handle errors for the setup command.
- `@app_commands.command async slash_name(interaction: discord.Interaction, *, name: str) -> None` — Change the name of a users channels.

## `wd_cogs.server.channel_utils` — `wd-cogs/src/wd_cogs/server/channel_utils.py`
Module containing Channel Utility commands.

### `@app_commands.guild_only class ChannelUtils(GroupCog, auto_load=True)`
Utility commands for managing channels.

- attributes: categories
- `@app_commands.checks.has_permissions @categories.command async slash_cat_delete(interaction: discord.Interaction, category: discord.CategoryChannel) -> None` — Delete a discord category with all channels inside.
- `@app_commands.command @app_commands.describe async slash_lock(interaction: discord.Interaction, target: discord.Member | discord.Role) -> None` — Lock a channel.
- `@app_commands.command @app_commands.describe async slash_unlock(interaction: discord.Interaction, target: discord.Member | discord.Role) -> None` — Unlock a channel.

## `wd_cogs.server.forum_dupe_finder` — `wd-cogs/src/wd_cogs/server/forum_dupe_finder.py`
Module for helping find duplicate forum posts.

### `class ForumDupeFinder(GroupCog, auto_load=True)`
A class to find duplicate forum posts based on their content.

- `get_ratio(a: str, b: str) -> float` — Calculate the similarity ratio between two strings.
- `find_duplicates(post_title: str, *, ratio: float=0.8) -> list[str]` — Find duplicate forum posts based on their content.

## `wd_cogs.server.gatekeeper` — `wd-cogs/src/wd_cogs/server/gatekeeper.py`
Gatekeeper cog for managing server roles and permissions, liming the amount of bot/spam users that can join.

### `@app_commands.guild_only class Gatekeeper(GroupCog, auto_load=True)`
Gatekeeper cog for limiting the amount of bot/spam users that can join.

- `@app_commands.command async slash_enable_gatekeeper(interaction: Interaction) -> None` — Enable the gatekeeper system. for the guild.
- `@app_commands.command async slash_disable_gatekeeper(interaction: Interaction) -> None` — Disable the gatekeeper system. for the guild.
- `@app_commands.command async slash_setup(interaction: Interaction, member_role: Role | None=None) -> None` — Set up the roles for the gatekeeper system.
- `async setup_roles(guild: Guild, member_role: Role | None=None) -> None` — Copy the default role permissions to the member role and removes all permissions from the default role.
- `@Cog.listener async on_member_join(member: Member) -> None` — When a member joins, check if they have accepted the rules and send them a message if not.
- `async send_verification_message(member: Member) -> None` — Send a verification message to the member.
- `check_user_accepted_rules(_member: discord.Member) -> bool` — Check if the user has accepted the rules.

## `wd_cogs.server.infractions` — `wd-cogs/src/wd_cogs/server/infractions.py`
Module for tracking infractions on users.

### `@app_commands.guilds class Infractions(GroupCog, auto_load=True)`
Track automod interaction from discord.

- `@Cog.listener async on_automod_rule_create(rule: AutoModRule) -> None` — Track new automod rules.
- `@Cog.listener async on_automod_rule_update(rule: AutoModRule) -> None` — Update automod rules.
- `@Cog.listener async on_automod_rule_delete(rule: AutoModRule) -> None` — Remove deleted automod rules.
- `@staticmethod get_severity(action: AutoModRuleAction) -> int` — Get the severity of the action.
- `@Cog.listener async on_automod_execution(execution: AutoModAction) -> None` — Add infractions when automod is executed.

## `wd_cogs.server.log_aggregator` — `wd-cogs/src/wd_cogs/server/log_aggregator.py`
Log aggregation and pagination system for persistent log viewing.

### `class LogEntry(NamedTuple)`
A single log entry containing an audit event embed.

- fields: embed: discord.Embed, timestamp: datetime, action: str

### `class LogAggregator(LoggerMixin)`
Manages aggregation of audit logs with pagination support.

- attributes: DEFAULT_MAX_LOGS
- `add_log(embed: discord.Embed, action: str) -> None` — Add a log entry to the aggregator.
- `async create_page_source() -> EmbedPageSource` — Create a page source for pagination from current logs.
- `async update_global_log_message(channel: discord.TextChannel, paginator_view: discord.ui.View) -> discord.Message` — Update or create the global log message in the specified channel.
- `get_log_count() -> int` — Get the current number of logs in the aggregator.
- `clear_logs() -> None` — Clear all logs from the aggregator.

## `wd_cogs.server.log_channels` — `wd-cogs/src/wd_cogs/server/log_channels.py`
Cog focused solely on provisioning and maintaining log channels.

- module names: MAX_CATEGORY_SIZE, GLOBAL

### `class LogChannels(GroupCog, auto_load=True)`
Manage log channel/category provisioning and synchronization.

- attributes: log_category_name
- `get_or_create_aggregator(guild_id: int) -> LogAggregator` — Get or create a log aggregator for a guild.
- `get_log_category(category_channels: list[CategoryChannel], current_count: int) -> CategoryChannel` — Get the log category for the current count of log channels.
- `async dispatch_aggregated_log(guild: discord.Guild, embed: discord.Embed, action: str) -> None` — Dispatch a log to the global aggregated channel.
- `@app_commands.command async slash_detect(interaction: discord.Interaction) -> None` — Detect existing log channels in the guild.
- `async detect_channels(interaction: discord.Interaction) -> AsyncGenerator[tuple[TextChannel, Channels]]` — Detect existing log channels in the guild, and updates them in the database, then yields them.
- `@app_commands.guild_only @app_commands.checks.has_permissions @app_commands.checks.bot_has_permissions @app_commands.checks.cooldown @app_commands.command async slash_log_add(interaction: discord.Interaction) -> None` — Create log channels for the guild. Creates category channels, to insert the channels into.
- `@app_commands.guild_only @app_commands.checks.has_permissions @app_commands.checks.bot_has_permissions @app_commands.command async slash_log_set(interaction: discord.Interaction, channel: discord.TextChannel, log_type: str) -> None` — Bind a Discord text channel to a given audit log action.
- `async create_categories(guild: Guild, bot_user: ClientUser, overwrites: PermissionsOverwrites) -> list[CategoryChannel]` — Create log categories and channels.
- `async create_log_channels(category_channels: list[CategoryChannel]) -> None` — Create log channels in the logging categories.
- `get_db_log_channels(guild: Guild) -> Sequence[Channels]` — Get all log channels from the database.
- `@app_commands.guild_only @app_commands.checks.has_permissions @app_commands.checks.bot_has_permissions @app_commands.checks.cooldown @app_commands.command async slash_log_remove(interaction: discord.Interaction) -> None` — Remove all log channels for this guild.
- `@app_commands.guilds @commands.is_owner @app_commands.command async slash_log_update(interaction: discord.Interaction, guild_id: int | None=None) -> None` — Update all log channels for the guild.
- `async update_log(guild: discord.Guild) -> None` — Update log channels for a guild.
- `async update_required_category_count(guild: discord.Guild, required_category_count: int) -> list[CategoryChannel]` — Update the required category count for the guild.
- `@slash_log_set.autocomplete async log_type_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]` — Autocomplete available audit log types for the set command.
- `get_valid_log_actions() -> list[str]` — Get a list of valid audit log actions.

## `wd_cogs.server.purge` — `wd-cogs/src/wd_cogs/server/purge.py`
A cog that provides a command to purge messages.

### `@runtime_checkable class Prunable(Protocol)`
A protocol that defines a prunable object.

- `async purge(*, limit: int | None=100, check: Callable[[Message], bool]=MISSING, before: SnowflakeTime | None=None, after: SnowflakeTime | None=None, around: SnowflakeTime | None=None, oldest_first: bool | None=None, bulk: bool=True, reason: str | None=None) -> list[Message]`

### `@runtime_checkable class History(Protocol)`
A protocol that defines a object with history.

- `history(*, limit: int | None=100, before: SnowflakeTime | None=None, after: SnowflakeTime | None=None, around: SnowflakeTime | None=None, oldest_first: bool | None=None) -> AsyncIterator[Message]`

### `@runtime_checkable class PrunableHistory(Prunable, History, Protocol)`
A protocol that defines a prunable channel with history.

### `@app_commands.guild_only @app_commands.checks.has_permissions class Purge(Cog, auto_load=True)`
A cog that provides a command to purge messages.

- attributes: limit, allow_history
- `@app_commands.command @app_commands.checks.has_permissions @app_commands.checks.bot_has_permissions async slash_purge(interaction: discord.Interaction, count: int, *, use_history: bool=False) -> None` — Purge X amount of messages, use history to delete older messages.
- `async history_delete(interaction: Interaction, count: int) -> list[discord.Message]` — Delete messages from the channel history. Rather than messages in cache. (Older messages).

## `wd_cogs.server.role_reminder` — `wd-cogs/src/wd_cogs/server/role_reminder.py`
Module to help remembering user roles when they leave and rejoin the server.

### `class AutoReAssign(GroupCog, auto_load=True)`
Cog to help re-assigning user roles when they leave and rejoin the server.

- attributes: auto_reassign_reason
- `@Cog.listener async on_member_remove(member: discord.Member) -> None` — When a member is kicked or banned, remember their roles for auto-assignment later.
- `remember_roles(member: discord.Member, entry: discord.AuditLogEntry) -> None` — When a member is kicked or banned, remember their roles for auto-assignment later.
- `@Cog.listener async on_member_join(member: discord.Member) -> None` — When a member joins, check if they have any roles to be auto-assigned.
- `@app_commands.command async slash_enable(interaction: discord.Interaction) -> None` — Enable the AutoReAssign feature for the guild.
- `@app_commands.command async slash_disable(interaction: discord.Interaction) -> None` — Disable the AutoReAssign feature for the guild.

## `wd_cogs.server.stats` — `wd-cogs/src/wd_cogs/server/stats.py`
Module that contains relevant classes to display stats about the guild.

- `get_peak_count(channel: Channels | discord.abc.GuildChannel) -> int` — Get the peak count from the channel name.

### `class StatChannel(LoggerMixin, ABC, metaclass=ABCMeta)`
Base class for all stat channels.

- attributes: update_reason
- `async update() -> None` — Update the channel name to display the current values.

### `class PeakStat(StatChannel)`
Class for the peak stat channel.

- `@property peak_count -> int` — Get the peak count from the channel name.
- `@property currently_online -> int` — Get the current number of online members.
- `async update() -> None` — Update the peak channel name to display the current peak.

### `class GuildStat(StatChannel)`
Class for the guild creation date channel.

- `async update() -> None` — Update the guild channel name to display the creation date.

### `class BotStat(StatChannel)`
Class for the bot stat channel.

- `async update() -> None` — Update the bot channel name to display the number of bots.

### `class UserStat(StatChannel)`
Class for the user stat channel.

- `@property user_count -> int` — Get the number of users in the channel.
- `async update() -> None` — Update the user channel name to display the number of users.

### `class OnlineStat(StatChannel)`
Class for the online stat channel.

- `@property online_count -> int` — Get the number of online users in the channel.
- `async update() -> None` — Update the online channel name to display the number of online users.

### `class StatChannels`
Container for all stat channels related to one guild.

### `@app_commands.guild_only class Stats(GroupCog, auto_load=True)`
Cog that contains all guild stats related commands.

- attributes: stats_update_interval
- `@Cog.listener async on_member_update(before: discord.Member, after: discord.Member) -> None` — Update the appropriate stats channels when a member update is fired.
- `async create_stats_channels(guild: discord.Guild | None, reason: str | None=None) -> None` — Create all stats channels for a guild.
- `async remove_stats_channels(guild: discord.Guild | None, reason: str | None=None) -> None` — Remove all stats channels for a guild.
- `async cog_load() -> None` — Load the cog.
- `@loop async update() -> None` — Update all stat channels periodically.
- `get_guild_stats_channels(guild: discord.Guild) -> tuple[PeakStat | None, GuildStat | None, BotStat | None, UserStat | None, OnlineStat | None]` — Get all stat channels for a guild.
- `@app_commands.command async slash_stats_show(interaction: discord.Interaction) -> None` — Show some stats about the guild.
- `@app_commands.checks.has_permissions @app_commands.checks.bot_has_permissions @app_commands.command async slash_stats_category_add(interaction: discord.Interaction) -> None` — Create stat channels.
- `@app_commands.command @app_commands.checks.has_permissions @app_commands.checks.bot_has_permissions async slash_stats_category_remove(interaction: discord.Interaction) -> None` — Remove stat channels.
- `@app_commands.command @app_commands.guilds @commands.is_owner async slash_reset_stats(interaction: discord.Interaction) -> None` — Reset all stats on the stat channels.

## `wd_cogs.server.sync_ban` — `wd-cogs/src/wd_cogs/server/sync_ban.py`
Logger mixin for database classes.

### `class SyncedBans(GroupCog, auto_load=True)`
Sync bans across all guilds that subscribe to this feature.

- attributes: sync
- `async create_banned_role(guild: discord.Guild) -> discord.Role` — Create a role for banned users.
- `@sync.command async slash_synced_ban_join(interaction: discord.Interaction) -> None` — Start syncing ban's with this guild.
- `@sync.command async slash_synced_ban_leave(interaction: discord.Interaction) -> None` — Stop syncing ban's with this guild.
- `@sync.command async slash_synced_ban_sync(interaction: discord.Interaction) -> None` — Ban all members lazy from all guilds that are synced.

## `wd_cogs.server.welcome` — `wd-cogs/src/wd_cogs/server/welcome.py`
Module to hold welcoming cogs.

### `class WelcomeMenu(Menu, SessionMixin)`
Menu for configuring welcome settings.

- `embed() -> discord.Embed` — Build the welcome settings embed.

### `class WelcomeMessageModal(Modal)`
Modal for editing the welcome message.

- attributes: message_input
- `async on_submit(interaction: discord.Interaction) -> None` — Handle modal submission and update the database.

### `@app_commands.guild_only @app_commands.checks.has_permissions class Welcome(Cog, auto_load=True)`
Cog containing the welcome commands.

- attributes: allowed_welcome_dm
- `@Cog.listener async on_member_join(member: discord.Member) -> None` — Send a welcome message to the user when they join the server.
- `@app_commands.command async slash_welcome(interaction: discord.Interaction) -> None` — Configure welcome message settings with an interactive menu.
