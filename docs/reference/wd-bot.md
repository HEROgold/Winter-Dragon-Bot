<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_bot` (wd-bot)
Core bot functionality.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_bot.auto_reload` — `wd-bot/src/wd_bot/auto_reload.py`
File-watcher based hot reload utilities for Discord cogs.

- module names: default_flags

### `class WatcherFlags(IntFlag)`
States for the auto-reload watcher.

- attributes: Enabled, Registered
- `@property is_enabled -> bool` — Check if the Enabled flag is set.
- `@property is_registered -> bool` — Check if the Registered flag is set.

### `class AutoReloadWatcher(LoggerMixin)`
Monitors extension files and reloads them in-place when they change.

- `register() -> None` — Start watching the cog's backing module.
- `deregister() -> None` — Stop watching the module when no cogs reference it anymore.

## `wd_bot.auto_sync` — `wd-bot/src/wd_bot/auto_sync.py`
Diff-based sync tracking for Discord application commands.

- module names: UNKNOWN_COMMAND_CODES
- `command_mention(session: Session, name: str, subcommand: str | None=None) -> str` — Return a clickable ``</name subcommand:id>`` mention of a globally synced command.
- `diff_global_commands(session: Session, commands: Sequence[CommandLike]) -> SyncPlan` — Compare ``commands`` against :class:`GlobalSyncedCommand` rows and plan the minimal sync.
- `diff_guild_commands(session: Session, guild_id: int, commands: Sequence[CommandLike]) -> SyncPlan` — Guild-scoped counterpart to :func:`diff_global_commands` (see class docstrings - unused in v1).

### `class CommandLike(Protocol)`
Anything with a stable name and a signature - satisfied structurally by wd_bot.commands.Command.

- fields: name: str
- `signature() -> str` — Return the command's signature string.

### `class SyncedRow(Protocol)`
One command's sync state in some scope - satisfied by :class:`GlobalSyncedCommand` and :class:`GuildSyncedCommand`.

- fields: command_id: int, signature: str, discord_command_id: str

### `class CommandRecord(SQLModel, table=True)`
The identity of a known command, independent of which scope(s) it's synced to.

- fields: name: str

### `class GlobalSyncedCommand(SQLModel, table=True)`
Tracks one command's global sync state: its last-synced signature and Discord's assigned ID.

- fields: command_id: int, signature: str, discord_command_id: str

### `class GuildSyncedCommand(SQLModel, table=True)`
Per-guild counterpart to :class:`GlobalSyncedCommand`.

- fields: command_id: int, guild_id: int, signature: str, discord_command_id: str

### `@dataclass class SyncPlan`
The set of REST calls needed to reconcile registered commands with Discord's actual state.

- fields: to_create: list[CommandLike], to_edit: list[tuple[CommandLike, str]], to_delete: list[str]

### `class SyncedCommands[Row: SyncedRow]`
The known command records and their synced rows in one scope (global, or one guild).

- `@classmethod load(session: Session, row_model: type[Row], *where: ColumnElement[bool] | bool) -> SyncedCommands[Row]` — Read every record, and the ``row_model`` rows matching ``where``, from ``session``.
- `row_for(name: str) -> Row | None` — Return the synced row for the command named ``name``, if it was synced in this scope.
- `is_synced(name: str, signature: str) -> bool` — Whether the command named ``name`` was last synced with exactly ``signature``.
- `plan(commands: Sequence[CommandLike]) -> SyncPlan` — Compute the :class:`SyncPlan` that brings this scope in line with ``commands``.

### `class CommandSyncer(ABC)`
Strategy for reconciling the bot's registered commands with Discord.

- `async sync(client: Client, commands: Sequence[AppCommand], *, allow_deletes: bool=True) -> None` — Push ``commands`` to Discord through ``client``, doing only the work needed.

### `class DefaultCommandSyncer(CommandSyncer, LoggerMixin)`
Diff-based :class:`CommandSyncer` tracking last-synced state in the database (global scope only).

- `async sync(client: Client, commands: Sequence[AppCommand], *, allow_deletes: bool=True) -> None` — Diff ``commands`` against the last-synced state and push only the changes to Discord.

## `wd_bot.bot` — `wd-bot/src/wd_bot/bot.py`
Module that contains the bot.

- module names: COMMAND_ERROR_REPLY

### `class BotConfig`
Basic bot configuration values.

- attributes: Intents, Permissions

### `class MissingError(Exception)`
Raised when a required attribute is missing.

### `class Bot(LoggerMixin)`
A forever-running Discord bot: connects to the gateway, loads extensions, dispatches events.

- fields: launch_time: datetime.datetime, loop: asyncio.AbstractEventLoop, client: Client, cogs: dict[str, Cog]
- `get_bot_invite() -> str` — Get the link to invite the bot to a server.
- `async add_cog(cog: Cog) -> None` — Register a cog and any of its @Cog.listener()-tagged methods.
- `@property syncer -> CommandSyncer` — The strategy used to push registered commands to Discord.
- `@property commands -> Generator[AppCommand]` — Yield every registered top-level command (plain commands and subcommand groups).
- `async sync_commands(client: Client) -> None` — Push the registered commands to Discord via :attr:`syncer`.
- `async get_extensions() -> AsyncGenerator[str]` — Get all extensions from :attr:`extensions_package`.
- `async load_extension(extension: str) -> None` — Load a single extension from :attr:`extensions_package`.
- `async load_extensions() -> None` — Load all cogs from :attr:`extensions_package`.
- `@with_known_exception @Config.with_kwarg async start(token: str) -> None` — Start the bot with a token from the config file, or a provided token. Provided token takes precedence.

## `wd_bot.cache` — `wd-bot/src/wd_bot/cache.py`
A cache for storing application commands, both globally and per guild.

### `class AppCommandCache`
A cache for storing application commands, both globally and per guild.

- `get_app_command(value: str, guild: Snowflake | int | None=None, *, fallback_to_global: bool=True) -> Mentionable | None` — Get an app command from the cache.
- `async update_app_commands_cache(bot: BotBase, commands: list[AppCommand] | None=None, guild: Snowflake | int | None=None) -> None` — Update the app commands cache with the provided commands for a given guild.
- `get_command_mention(command: Command | str) -> str` — Return a command string from a given functiontype. (Decorated with app_commands.command).

## `wd_bot.cogs` — `wd-bot/src/wd_bot/cogs.py`
Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency.

- module names: default_flags
- `command(name: str, description: str, default_member_permissions: Permissions | None=None, contexts: Iterable[InteractionContextType] | None=None) -> Callable[[Callable[..., Awaitable[None]]], Command]` — Tag a Cog method as a chat-input application command, building a :class:`Command` for it.
- `component(prefix: str) -> Callable[[Callable[..., Awaitable[None]]], ComponentHandler]` — Tag a Cog method as the handler for components whose ``custom_id`` starts with ``prefix``.

### `class BotArgs(TypedDict)`
TypedDict for bot arguments.

- fields: bot: Required[Bot], db_session: NotRequired[Session]

### `class CogFlags(IntFlag)`
Flags for Cog behavior.

- attributes: AutoLoad, AutoReload

### `class Cog(LoggerMixin)`
A wd-native feature unit: a class whose methods can be tagged with @Cog.listener().

- fields: bot: Bot, flags: CogFlags
- attributes: listener, command, component
- `async auto_load() -> None` — Load the cog if auto_load is True.
- `@classmethod commands() -> Generator[Command]` — Yield the :class:`Command` attributes defined on this cog class or inherited from its bases.
- `@classmethod app_commands() -> Generator[AppCommand]` — Yield what this cog registers as top-level Discord commands: each of its commands.
- `@classmethod components() -> Generator[ComponentHandler]` — Yield the :class:`ComponentHandler` attributes defined on this cog class or inherited from its bases.
- `mention(command: Command) -> str` — Return a clickable mention of ``command``, or its plain ``/name`` until it has been synced.
- `@property bind -> Engine | Connection` — The database the cog's injected session connects to; open short-lived sessions on it per operation.
- `create_tables(*models: type[SQLModel]) -> None` — Create the tables of ``models`` that don't exist yet, in :attr:`bind`; each named after its model, lowercased.
- `async load() -> None` — Run setup once registered with the bot; a hook for subclasses to override.
- `async unload() -> None` — Unregister any auto-reload watcher.

### `class GroupCog(Cog)`
A cog whose commands are registered as subcommands of one Discord command, ``/<group_name> <command>``.

- fields: group_name: ClassVar[str], group_description: ClassVar[str], group_default_member_permissions:
  ClassVar[Permissions | None], group_contexts: ClassVar[list[InteractionContextType] | None]
- `@classmethod app_commands() -> Generator[AppCommand]` — Yield this cog's single top-level Discord command: the group holding its commands.
- `mention(command: Command) -> str` — Return a clickable mention of the subcommand ``command``, as ``/<group> <command>``.

## `wd_bot.commands` — `wd-bot/src/wd_bot/commands.py`
Application commands: the shared :class:`AppCommand` base, plain :class:`Command` and :class:`CommandGroup`.

- `type AutocompleteHandler = Callable[..., Awaitable[Iterable[ApplicationCommandOptionChoice]]]`

### `class AppCommand(LoggerMixin, ABC)`
What every application command shares: its name, description and where Discord lets it be used.

- `options() -> Generator[ApplicationCommandOption]` — Yield this command's Discord option definitions.
- `async invoke(cog: Cog, interaction: CommandInteraction) -> bool` — Handle ``interaction``; return ``False`` if the handler failed or nothing could be dispatched.
- `async complete(cog: Cog, interaction: AutocompleteInteraction) -> bool` — Suggest values for the option being typed; return ``False`` if the handler failed or none was found.
- `signature() -> str` — Return the signature of the full registered definition, used to detect drift for sync.
- `params() -> ApplicationCommandParams` — Return the create/edit request body for this command.

### `class Command(AppCommand)`
Encapsulates one chat-input application command: its Discord definition and its handler.

- `options() -> Generator[ApplicationCommandOption]` — Yield this command's Discord option definitions, derived from its handler's parameters.
- `autocomplete(option: str) -> Callable[[AutocompleteHandler], AutocompleteHandler]` — Tag a Cog method as the handler suggesting values for this command's ``option`` while it's typed.
- `async invoke(cog: Cog, interaction: CommandInteraction, options: Sequence[InteractionDataOption] | None=None) -> bool` — Resolve option values into kwargs and call the wrapped handler.
- `async complete(cog: Cog, interaction: AutocompleteInteraction, options: Sequence[InteractionDataOption] | None=None) -> bool` — Answer ``interaction`` with the focused option's suggestions.

### `class CommandGroup(AppCommand)`
A chat-input command whose options are subcommands, built from a :class:`~wd_bot.cogs.GroupCog`.

- `options() -> Generator[ApplicationCommandOption]` — Yield one SUB_COMMAND option per subcommand, nesting that subcommand's own options.
- `async invoke(cog: Cog, interaction: CommandInteraction) -> bool` — Route ``interaction`` to the chosen subcommand, passing it that subcommand's option values.
- `async complete(cog: Cog, interaction: AutocompleteInteraction) -> bool` — Route ``interaction`` to the chosen subcommand's autocomplete, like :meth:`invoke`.

## `wd_bot.components` — `wd-bot/src/wd_bot/components.py`
Message-component handlers: route a clicked component to the Cog method owning its ``custom_id`` prefix.

- module names: CUSTOM_ID_SEPARATOR
- `parse_custom_id(custom_id: str) -> tuple[str, list[str]]` — Split ``custom_id`` into its handler prefix and the args after it.

### `class ComponentHandler(LoggerMixin)`
A Cog method handling every component whose ``custom_id`` starts with :attr:`prefix`.

- `custom_id(*args: str | int) -> str` — Build a ``custom_id`` routed to this handler, carrying ``args``.
- `async invoke(cog: Cog, interaction: ComponentInteraction, args: Sequence[str]) -> bool` — Call the handler; return ``False`` if it raised (the exception is logged).

## `wd_bot.extensions` — `wd-bot/src/wd_bot/extensions.py`
Finding the extension modules a bot loads its cogs from.

### `class ExtensionDiscovery`
Lists the modules inside an extensions package, at any depth.

- `modules() -> Generator[str]` — Yield every module (not package) under :attr:`package`, named relative to it.

## `wd_bot.help` — `wd-bot/src/wd_bot/help.py`
Module for defining the help command.

- module names: default_help

### `class HelpCommand(View, Command)`
The help command.

### `class DefaultHelpCommand(HelpCommand)`
Default implementation for a simple help command.

## `wd_bot.listener` — `wd-bot/src/wd_bot/listener.py`
Runtime `listener()` decorator: tag a Cog method as a gateway dispatch-event listener.

- `listener(name: str | None=None) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]` — Tag a Cog method as a gateway dispatch-event listener.

## `wd_bot.paths` — `wd-bot/src/wd_bot/paths.py`
Centralized filesystem paths shared across the bot codebase.

- module names: BOT_CONFIG, CORE_DIR, PACKAGE_DIR, ROOT_DIR, EXTENSIONS, DYNAMIC_DIR, IMG_DIR, METRICS_FILE

## `wd_bot.permissions` — `wd-bot/src/wd_bot/permissions.py`
Module for handling permission related things in Discord bot interactions.

### `class PermissionsNotifier`
Notify users about missing permissions, roles or overwrites.

- `async notify() -> None` — Notify the user about missing permissions, roles or overwrites.

## `wd_bot.signature` — `wd-bot/src/wd_bot/signature.py`
Derive a stable signature string for a command's callable, used to detect definition drift.

- `command_signature(func: Callable[..., object]) -> str` — Return a stable string form of ``func``'s signature, used to detect when it has changed.
