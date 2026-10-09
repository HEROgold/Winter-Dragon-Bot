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
Keeps the commands Discord has equal to the :class:`~wd_bot.registry.CommandRegistry`, one scope at a time.

### `class CommandSyncer(LoggerMixin)`
Brings Discord's commands in line with a :class:`~wd_bot.registry.CommandRegistry`.

- `async sync(client: Client, scopes: Iterable[Scope], *, allow_writes: bool=True) -> None` — Sync each of ``scopes``; with ``allow_writes`` False, only read them (recovering IDs), never PUT.

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
- `async remove_cog(cog: Cog) -> set[Scope]` — Unregister ``cog``'s listeners, commands and components and unload it; return the command scopes that changed.
- `@property commands -> Generator[AppCommand]` — Yield every registered top-level command (plain commands and subcommand groups).
- `async sync_commands(client: Client, scopes: Iterable[Scope] | None=None) -> None` — Sync ``scopes`` (default: every scope the registry knows) to Discord via :attr:`syncer`.
- `async get_extensions() -> AsyncGenerator[str]` — Get all extensions from :attr:`extensions_package`.
- `async reload_extension(module_name: str) -> None` — Re-import the extension module ``module_name``, swap its cogs for fresh ones and sync what changed.
- `async load_extension(extension: str) -> None` — Load a single extension from :attr:`extensions_package`.
- `async load_extensions() -> None` — Load all cogs from :attr:`extensions_package`.
- `@with_known_exception @Config.with_kwarg async start(token: str) -> None` — Start the bot with a token from the config file, or a provided token. Provided token takes precedence.

## `wd_bot.checks` — `wd-bot/src/wd_bot/checks.py`
Checks a command makes before acting: whether the invoker holds some permissions, or owns the bot.

- `member_has(interaction: AnyInteraction, permissions: Permissions) -> bool` — Whether the guild member invoking ``interaction`` holds every one of ``permissions`` in its channel.
- `owner_ids(application: Application) -> Generator[Snowflake]` — Yield the IDs of the users owning ``application``: its team's accepted members, or else its owner.
- `async is_owner(client: Client, user_id: SnowflakeLike) -> bool` — Whether the user ``user_id`` owns the bot; ``False`` when the application can't be read.

## `wd_bot.cogs` — `wd-bot/src/wd_bot/cogs.py`
Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency.

- module names: default_flags
- `command(name: str, description: str, default_member_permissions: Permissions | None=None, contexts: Iterable[InteractionContextType] | None=None, guild_ids: Iterable[SnowflakeLike] | None=None) -> Callable[[Callable[..., Awaitable[None]]], Command]` — Tag a Cog method as a chat-input application command, building a :class:`Command` for it.
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
- `@classmethod path_of(command: Command) -> CommandPath` — Return the path a user types to run ``command`` from this cog: ``/name``.
- `mention(command: Command, *, guild: SnowflakeLike | None=None) -> CommandMention` — Return a mention of ``command``, as seen from ``guild``: clickable once Discord reported it, else ``/name``.
- `@property bind -> Engine | Connection` — The database the cog's injected session connects to; open short-lived sessions on it per operation.
- `create_tables(*models: type[SQLModel]) -> None` — Create the tables of ``models`` that don't exist yet, in :attr:`bind`; each named after its model, lowercased.
- `async load() -> None` — Run setup once registered with the bot; a hook for subclasses to override.
- `async unload() -> None` — Unregister any auto-reload watcher.

### `class GroupCog(Cog)`
A cog whose commands are registered as subcommands of one Discord command, ``/<group_name> <command>``.

- fields: group_name: ClassVar[str], group_description: ClassVar[str], group_default_member_permissions:
  ClassVar[Permissions | None], group_contexts: ClassVar[list[InteractionContextType] | None], group_guild_ids:
  ClassVar[list[SnowflakeLike] | None]
- `@classmethod app_commands() -> Generator[AppCommand]` — Yield this cog's single top-level Discord command: the group holding its commands.
- `@classmethod path_of(command: Command) -> CommandPath` — Return the path a user types to run the subcommand ``command``: ``/<group> <command>``.

## `wd_bot.commands` — `wd-bot/src/wd_bot/commands.py`
Application commands: the shared :class:`AppCommand` base, plain :class:`Command` and :class:`CommandGroup`.

- `type AutocompleteHandler = Callable[..., Awaitable[Iterable[ApplicationCommandOptionChoice]]]`

### `class ChannelTypes`
Limit a channel option to some kinds of channel: ``category: Annotated[Channel, ChannelTypes(GUILD_CATEGORY)]``.

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

## `wd_bot.registry` — `wd-bot/src/wd_bot/registry.py`
Which application commands the bot registers where, and the IDs Discord gave them.

- module names: GLOBAL: Final
- `declared_scopes(command: AppCommand) -> frozenset[Scope]` — Place ``command`` in the scopes it declares (global unless it names guilds); the default :class:`Placement`.
- `definition_matches(local: ApplicationCommandParams, remote: ApplicationCommand) -> bool` — Whether Discord's ``remote`` command has the definition ``local`` would register.

### `@dataclass class Scope`
Where a command is registered: globally (``guild_id=None``) or in one guild.

- fields: guild_id: Snowflake | None

### `@dataclass class CommandPath`
The full name a user types: ``/root`` or ``/root sub``.

- fields: root: str, sub: str | None

### `class Placement(Protocol)`
Decides which scopes a top-level command is registered in.

- `__call__(command: AppCommand, /) -> frozenset[Scope]` — Return the scopes ``command`` belongs in.

### `@dataclass class Entry`
A registered top-level command and the cog whose methods handle it.

- fields: cog: Cog, command: AppCommand

### `@dataclass class CommandMention`
A mention of a command, resolved to its current Discord ID when rendered (``str()`` or an f-string).

- fields: registry: CommandRegistry, path: CommandPath, guild_id: Snowflake | None

### `class CommandRegistry(LoggerMixin)`
The bot's commands per scope, next to what Discord last reported for that scope.

- `register(cog: Cog) -> set[Scope]` — Add ``cog``'s top-level commands to the scopes their placement picks; return those scopes.
- `unregister(cog: Cog) -> set[Scope]` — Remove ``cog``'s commands from every scope; return the scopes that changed.
- `refresh() -> set[Scope]` — Place every registered command again, e.g. after :attr:`placement` changed; return the scopes that changed.
- `scopes_of(cog: Cog) -> set[Scope]` — Return the scopes ``cog`` has commands registered in.
- `entry(name: str, guild_id: Snowflake | None=None) -> Entry | None` — Return the command ``name`` an interaction from ``guild_id`` reaches: the guild's own first, then global.
- `entries(scope: Scope) -> Generator[Entry]` — Yield the commands registered in ``scope``, by name.
- `commands() -> Generator[AppCommand]` — Yield every registered top-level command once, whichever scopes it is in.
- `scopes() -> set[Scope]` — Return every scope that has commands locally or on Discord; a sync covers all of them.
- `params(scope: Scope) -> list[ApplicationCommandParams]` — Return the definitions ``scope`` should have on Discord, by name.
- `is_known(scope: Scope) -> bool` — Whether Discord has reported ``scope``'s commands since startup (or the last :meth:`forget`).
- `apply(scope: Scope, commands: Iterable[ApplicationCommand]) -> None` — Record ``commands`` as everything Discord has in ``scope`` now.
- `forget() -> None` — Drop what Discord reported, so the next sync reads every scope from Discord again.
- `in_sync(scope: Scope) -> bool` — Whether Discord's last report for ``scope`` has exactly the commands and definitions the bot wants.
- `is_synced(scope: Scope, name: str) -> bool` — Whether the command ``name`` in ``scope`` is on Discord as currently defined.
- `command_id(name: str, guild_id: Snowflake | None=None) -> Snowflake | None` — Return the Discord ID of the top-level command ``name``: the guild's own first, then the global one.
- `mention(path: CommandPath, guild_id: Snowflake | None=None) -> CommandMention` — Return a mention of the command at ``path``, as seen from ``guild_id``.

## `wd_bot.signature` — `wd-bot/src/wd_bot/signature.py`
Derive a stable signature string for a command's callable, used to detect definition drift.

- `command_signature(func: Callable[..., object]) -> str` — Return a stable string form of ``func``'s signature, used to detect when it has changed.
