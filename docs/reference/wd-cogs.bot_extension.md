<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_cogs.bot_extension` (wd-cogs)
Package that contains extensions for WinterDragon bot.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_cogs.bot_extension` — `wd-cogs/src/wd_cogs/bot_extension/__init__.py`

- exports: BotActivity, BotControl, BotMetrics, CogEvents , CommandManager, Prometheus, Sync

## `wd_cogs.bot_extension.bot_activity` — `wd-cogs/src/wd_cogs/bot_extension/bot_activity.py`
Module for bot activity and status management.

- module names: INVALID_RNG_STATUS, INVALID_RNG_ACTIVITY

### `@app_commands.guilds class BotActivity(GroupCog, auto_load=True)`
Cog to control the bot's activity and status.

- attributes: random_activity, periodic_change, periodic_time
- `async cog_load() -> None` — When the cog loads, start activity statuses.
- `@loop async activity_switch() -> None` — Switch the bot's activity and status periodically. Uses activity.periodic_time config.
- `get_random_activity() -> tuple[discord.Status, discord.Activity]` — Get a random valid activity and status.
- `@commands.is_owner @app_commands.command async slash_bot_activity(interaction: discord.Interaction, status: str, activity: str, msg: str='') -> None` — Change the bot's activity and status.
- `@slash_bot_activity.autocomplete async activity_autocomplete_status(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]` — Autocomplete for the status command.
- `@slash_bot_activity.autocomplete async activity_autocomplete_activity(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]` — Autocomplete for the activity command.
- `@activity_switch.before_loop async before_update() -> None` — Wait until the bot is ready before starting the loops.

## `wd_cogs.bot_extension.bot_control` — `wd-cogs/src/wd_cogs/bot_extension/bot_control.py`
Module that contains interfaces to control the bot using discord.

### `@app_commands.guilds class BotControl(GroupCog, auto_load=True)`
Cog to control the bot.

- `@commands.is_owner @app_commands.guild_only @app_commands.command async slash_bot_announce(interaction: discord.Interaction, msg: str) -> None` — Announce a message to all servers the bot is in and allowed to.

## `wd_cogs.bot_extension.bot_metrics` — `wd-cogs/src/wd_cogs/bot_extension/bot_metrics.py`
Module for bot performance metrics and monitoring.

- `codeblock(language: str, text: str | float) -> str` — Return a codeblock with ansi colors.

### `@app_commands.guilds class BotMetrics(GroupCog, auto_load=True)`
Cog for monitoring bot performance metrics.

- fields: timestamps: list[float], cpu_percentages: list[float], net_io_counters: list[psutil._ntp.snetio],
  ram_percentages: list[float], bytes_sent: list[int], bytes_received: list[int], packets_sent: list[int],
  packets_received: list[int]
- attributes: gather_metrics_interval, cleanup_interval, metrics_file
- `async cog_load() -> None` — When the cog loads, start collecting metrics.
- `@app_commands.command @commands.is_owner async slash_ping(interaction: discord.Interaction) -> None` — Show the bot's latency.
- `async gather_latency(interaction: discord.Interaction) -> tuple[int, int, int]` — Gather the latency, response time and database response time of the bot.
- `@app_commands.command async slash_performance(interaction: discord.Interaction) -> None` — Show the bot's performance.
- `@commands.is_owner @app_commands.command async slash_performance_graph(interaction: discord.Interaction) -> None` — Show the bot's performance in a graph.
- `@staticmethod get_colors(value: float, max_amount: int) -> tuple[str, int]` — Get colors based on given max value, with predefined percentages.
- `@classmethod get_latency_colors(latency: int) -> tuple[str, int]` — Get colors based on latency.
- `@classmethod get_percentage_colors(percentage: int) -> tuple[str, int]` — Get colors based on percentage.
- `@classmethod get_bytes_colors(bytes_count: int) -> tuple[str, int]` — Get colors based on bytes.
- `@classmethod get_packets_colors(packets_count: int) -> tuple[str, int]` — Get colors based on packets.
- `@loop async gather_metrics_loop() -> None` — Gather system metrics every second.
- `gather_system_metrics() -> None` — Gather system metrics like cpu, ram and network traffic.
- `plot_system_metrics() -> None` — Plot the system metrics on a graph.
- `@gather_metrics_loop.before_loop async before_update() -> None` — Wait until the bot is ready before starting the loops.

## `wd_cogs.bot_extension.command_manager` — `wd-cogs/src/wd_cogs/bot_extension/command_manager.py`
Cog for managing command enablement/disablement with interactive UI.

### `class CommandToggleButton(ToggleButton)`
A button to toggle a command's enabled/disabled state.

### `class CommandManagementPageSource(PageSource[list[tuple[str, bool]]])`
Page source for displaying commands with toggle buttons.

- `async get_page(page_number: int) -> list[tuple[str, bool]]` — Get a page of commands with their toggle states.
- `async get_page_count() -> int` — Get total page count.
- `async format_page(page_data: list[tuple[str, bool]], page_number: int) -> tuple[str, discord.Embed]` — Format the page as an embed with command toggles.

### `class CommandManagementView(View)`
View for managing command enablement with toggle buttons and apply button.

- `get_command_state(command_name: str) -> bool` — Get the current state of a command.
- `set_command_state(command_name: str, *, state: bool) -> None` — Set the state of a command.
- `async on_paginator_page_change(current_page: int) -> None` — Paginator page changed.
- `async on_apply(interaction: Interaction) -> None` — Handle the apply button click.

### `class CommandManager(Cog, auto_load=True)`
Cog for managing command enablement/disablement with interactive UI.

- `@app_commands.command @app_commands.guild_only async manage_commands(interaction: Interaction) -> None` — Open the command manager to enable/disable commands for the guild.

## `wd_cogs.bot_extension.database_manager` — `wd-cogs/src/wd_cogs/bot_extension/database_manager.py`
Module for tracking user, guild, role and channel data in the database.

### `class OnGuildChannelUpdate(AuditEvent, action=AuditLogAction.channel_update)`
Event listener for guild channel updates.

- `async handle() -> None` — When a channel is updated, update it in the database.
- `create_embed() -> discord.Embed`

### `class OnRoleCreate(AuditEvent, action=AuditLogAction.role_create)`
Event listener for role creation.

- `async handle() -> None` — When a role is created, add it to the database.

### `class OnRoleDelete(AuditEvent, action=AuditLogAction.role_delete)`
Event listener for role deletion.

- `async handle() -> None` — When a role is deleted, remove it lazy from the database.

### `class OnMessageDelete(AuditEvent, action=AuditLogAction.message_delete)`
Event listener for message deletion.

- `async handle() -> None` — When a message is deleted, remove it lazy from the database.

### `class OnGuildRoleCreate(AuditEvent, action=AuditLogAction.role_create)`
Event listener for guild role creation.

- `async handle() -> None` — When a role is created, add it to the database.

### `class OnGuildRoleDelete(AuditEvent, action=AuditLogAction.role_delete)`
Event listener for guild role deletion.

- `async handle() -> None` — When a role is deleted, remove it lazy from the database.

### `class OnGuildRoleUpdate(AuditEvent, action=AuditLogAction.role_update)`
Event listener for guild role updates.

- `async handle() -> None` — When a role is updated, update it in the database.

### `class OnPresenceUpdate(AuditEvent, action=AuditLogAction.member_update)`
Event listener for presence updates.

- `async handle() -> None` — Code to run whenever a presence is updated, to keep track of a users online status.

### `class CogEvents(Cog, auto_load=True)`
Cog to register event listeners for audit log events, that are unable to be tracked via Audit Logs.

- `@Cog.listener async on_message(message: discord.Message) -> None` — When a message is sent by any user, add it to the database.
- `@Cog.listener async on_interaction(interaction: discord.Interaction) -> None` — Log interaction usage to the database.

## `wd_cogs.bot_extension.prometheus` — `wd-cogs/src/wd_cogs/bot_extension/prometheus.py`
.

### `class Prometheus(Cog, auto_load=False)`
Prometheus integration for the bot.

- `@loop async init() -> None` — Initialize the Prometheus cog.
- `@init.before_loop async before_init() -> None` — Wait until the bot is ready before starting the loops.

## `wd_cogs.bot_extension.sync` — `wd-cogs/src/wd_cogs/bot_extension/sync.py`
Module to sync slash commands with the Discord API.

- module names: COMMAND_DESCRIPTION_LIMIT, COMMAND_NAME_LIMIT, EMBED_FIELD_DESC_LIMIT, ellipses
- `sync_name(command: CommandLike, logger: Logger) -> str` — Return the name used for syncing the command.
- `sync_description(command: CommandLike, logger: Logger) -> str` — Return the description used for syncing the command.

### `class CommandLike(Protocol)`
Protocol for command like objects.

- `@property name -> str` — Command name.
- `@property qualified_name -> str` — Fully qualified command name.
- `@property description -> str` — Command description.

### `class SyncedCommandsPageSource(PageSource[list[dict[str, str]]])`
Page source for displaying synced commands in an embed.

- `async get_page(page_number: int) -> list[dict[str, str]]` — Get a page of commands.
- `async get_page_count() -> int` — Get total page count.
- `async format_page(page_data: list[dict[str, str]], page_number: int) -> tuple[str, discord.Embed]` — Format the page as an embed with command listings.

### `class LenFixer(LoggerMixin)`
Context manager to temporarily fix command name/description length.

### `class Sync(Cog, auto_load=True)`
Sync slash commands with the Discord API.

- `@app_commands.command async slash_sync(interaction: discord.Interaction) -> None` — Sync all commands on the current guild.
- `@commands.is_owner @commands.hybrid_command async slash_sync_hybrid(ctx: commands.Context) -> None` — Sync all commands on all servers. This is a ctx and slash command (hybrid).
- `async sync_local(guild: Guild) -> list[AppCommand]` — Sync all commands on a specific guild.
- `async sync_global() -> list[AppCommand]` — Sync all globally available commands.
