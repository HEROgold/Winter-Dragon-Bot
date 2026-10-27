<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_api_reference.py -->

# `wd_bot` (wd-bot)
Core bot functionality.

Public names only — open the file when you need a body. Index: [API reference](index.md).

## `wd_bot.application` — `wd-bot/src/wd_bot/application.py`
The bot's application ID: asked from Discord once at startup, never configured.

### `class ApplicationId`
The ID of the application the bot token belongs to, kept for the rest of the process.

- fields: value: ClassVar[Snowflake | None]
- `@classmethod async load(client: Client) -> Snowflake` — Fetch the ID of ``client``'s application, keep it in :attr:`value` and return it.
- `@classmethod get() -> Snowflake` — Return the ID :meth:`load` fetched.

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

- `invite_url() -> str` — Return the link to invite the bot to a server, with the scopes and permissions in ``bot.ini``.

### `class Bot(LoggerMixin)`
A forever-running Discord bot: connects to the gateway, loads extensions, dispatches events.

- fields: launch_time: datetime.datetime, loop: asyncio.AbstractEventLoop, client: Client, cogs: dict[str, Cog]
- `async add_cog(cog: Cog) -> None` — Register a cog's commands, listeners and component handlers, load it, then start its periodic tasks.
- `async remove_cog(cog: Cog) -> set[Scope]` — Unregister ``cog``'s handlers, stop its periodic tasks and unload it; return the command scopes that changed.
- `@property commands -> Generator[AppCommand]` — Yield every registered top-level command (plain commands and subcommand groups).
- `async sync_commands(client: Client, scopes: Iterable[Scope] | None=None) -> None` — Sync ``scopes`` (default: every scope the registry knows) to Discord via :attr:`syncer`.
- `async reload_extension(module_name: str) -> None` — Reload the extension module ``module_name`` via :attr:`extensions`, then sync the command scopes it changed.
- `@with_known_exception @BotConfig.with_kwarg async start(token: str) -> None` — Start the bot with the token from bot.ini.

## `wd_bot.checks` — `wd-bot/src/wd_bot/checks.py`
Checks made before a command or component acts, and answering the user when one refuses.

- module names: SHOWN_NAMES
- `member_has(interaction: AnyInteraction, permissions: Permissions) -> bool` — Whether the guild member invoking ``interaction`` holds every one of ``permissions`` in its channel.
- `permission_names(permissions: Permissions) -> str` — Return ``permissions`` as Discord's client shows them: ``Manage Channels and Manage Server``.
- `require_permissions(interaction: AnyInteraction, permissions: Permissions) -> None` — Refuse unless the member invoking ``interaction`` holds every one of ``permissions``.
- `require_guild(interaction: CommandInteraction | ComponentInteraction) -> GuildCommandInteraction | GuildComponentInteraction` — Return ``interaction`` as sent from a guild, or refuse when it wasn't.
- `async answer_refusal(interaction: AnyInteraction, refused: Refused) -> None` — Tell the user behind ``interaction``, privately, why their action was refused.
- `owner_ids(application: Application) -> Generator[Snowflake]` — Yield the IDs of the users owning ``application``: its team's accepted members, or else its owner.
- `async is_owner(client: Client, user_id: SnowflakeLike) -> bool` — Whether the user ``user_id`` owns the bot; ``False`` when the application can't be read.

## `wd_bot.cogs` — `wd-bot/src/wd_bot/cogs.py`
Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency.

- module names: default_flags
- `command(name: str, description: str, *, requires: Permissions | None=None, **options: Unpack[DefinitionOptions]) -> Callable[[Callable[..., Awaitable[None]]], Command]` — Tag a Cog method as a chat-input application command, building a :class:`Command` for it.
- `component(prefix: str) -> Callable[[Callable[..., Awaitable[None]]], ComponentHandler]` — Tag a Cog method as the handler for components whose ``custom_id`` starts with ``prefix``.
- `modal(prefix: str) -> Callable[[Callable[..., Awaitable[None]]], ModalHandler]` — Tag a Cog method as the handler for modal submits whose ``custom_id`` starts with ``prefix``.
- `periodic(seconds: Seconds) -> Callable[[Callable[..., Awaitable[float | None]]], PeriodicTask]` — Tag a Cog method as a tick the bot runs every ``seconds`` while the cog is loaded; see :class:`PeriodicTask`.

### `class BotArgs(TypedDict)`
TypedDict for bot arguments.

- fields: bot: Required[Bot], db_session: NotRequired[Session]

### `class CogFlags(IntFlag)`
Flags for Cog behavior.

- attributes: AutoLoad, AutoReload

### `class Cog(LoggerMixin)`
A wd-native feature unit: a class whose methods can be tagged with @Cog.listener().

- fields: bot: Bot, flags: CogFlags
- attributes: listener, command, component, modal, periodic
- `async auto_load() -> None` — Load the cog if auto_load is True.
- `@classmethod attributes_of[T](kind: type[T]) -> Generator[T]` — Yield the ``kind`` attributes defined on this cog class or inherited from its bases, by attribute name.
- `@classmethod commands() -> Generator[Command]` — Yield the :class:`Command` attributes defined on this cog class or inherited from its bases.
- `@classmethod app_commands() -> Generator[AppCommand]` — Yield what this cog registers as top-level Discord commands: each of its commands.
- `@classmethod components() -> Generator[ComponentHandler]` — Yield the :class:`ComponentHandler` attributes defined on this cog class or inherited from its bases.
- `@classmethod modals() -> Generator[ModalHandler]` — Yield the :class:`ModalHandler` attributes defined on this cog class or inherited from its bases.
- `@classmethod periodic_tasks() -> Generator[PeriodicTask]` — Yield the :class:`PeriodicTask` attributes defined on this cog class or inherited from its bases.
- `start_periodic_tasks() -> None` — Start every periodic task of this cog; :meth:`wd_bot.bot.Bot.add_cog` calls it after :meth:`load`.
- `async stop_periodic_tasks() -> None` — Cancel this cog's periodic tasks and wait until they've stopped; :meth:`wd_bot.bot.Bot.remove_cog` calls it.
- `@classmethod path_of(command: Command) -> CommandPath` — Return the path a user types to run ``command`` from this cog: ``/name``.
- `@classmethod guild_only() -> bool` — Whether the cog is used in guilds only: every one of its commands is; its components inherit this.
- `@classmethod check_guild_handlers() -> None` — Raise :class:`TypeError` if a handler expects a guild interaction it wouldn't get.
- `@classmethod audit_reason(interaction: AnyInteraction, command: Command, action: str) -> str` — Return the audit-log reason for ``action``: what was done, by whom, with which command.
- `mention(command: Command, *, guild: SnowflakeLike | None=None) -> CommandMention` — Return a mention of ``command``, as seen from ``guild``: clickable once Discord reported it, else ``/name``.
- `@property bind -> Engine | Connection` — The database the cog's injected session connects to; open short-lived sessions on it per operation.
- `create_tables(*models: type[SQLModel]) -> None` — Make sure the tables of ``models`` exist in :attr:`bind`; see :func:`wd_db.schema.ensure_tables`.
- `async load() -> None` — Run setup once registered with the bot; a hook for subclasses to override.
- `async unload() -> None` — Unregister any auto-reload watcher.

### `class GroupCog(Cog)`
A cog whose commands are registered as subcommands of one Discord command, ``/<group> <command>``.

- fields: group_definition: ClassVar[CommandDefinition]
- `@classmethod app_commands() -> Generator[AppCommand]` — Yield this cog's single top-level Discord command: the group holding its commands.
- `@classmethod path_of(command: Command) -> CommandPath` — Return the path a user types to run the subcommand ``command``: ``/<group> <command>``.
- `@classmethod guild_only() -> bool` — Whether the group is offered in guilds only; its subcommands and components then get guild interactions.

## `wd_bot.commands` — `wd-bot/src/wd_bot/commands.py`
Application commands: the shared :class:`AppCommand` base, plain :class:`Command` and :class:`CommandGroup`.

- module names: GUILD_INTERACTIONS
- `type AutocompleteHandler = Callable[..., Awaitable[Iterable[ApplicationCommandOptionChoice]]]`
- `wants_guild_interaction(func: Callable[..., object]) -> bool` — Whether ``func``'s ``interaction`` parameter is annotated as a guild interaction.

### `class ChannelTypes`
Limit a channel option to some kinds of channel: ``category: Annotated[Channel, ChannelTypes(GUILD_CATEGORY)]``.

### `class Describe`
Give an option the description Discord shows under it: ``reason: Annotated[str, Describe("Why")]``.

### `class Length`
Limit a string option's length: ``name: Annotated[str, Length(min_length=2, max_length=32)]``.

### `class Range`
Limit an ``int`` or ``float`` option's value: ``count: Annotated[int, Range(min_value=1, max_value=10)]``.

### `class Lookup`
Suggest an option's values while it's typed: ``name: Annotated[str, Lookup(pet_names)]``.

- `@staticmethod choice(row: LifecycleModel, name: str) -> ApplicationCommandOptionChoice` — Return the suggestion that picks ``row``, shown as ``name`` cut to Discord's length limit.
- `load(cog: Cog, models: tuple[type[LifecycleModel], ...], option: str, value: object) -> LifecycleModel` — Return the alive row ``value`` names, one of ``models``; raise ``Refused`` when there is none.

### `@dataclass class OptionSpec`
A handler parameter as a Discord option: what Discord asks for, and what the handler gets.

- fields: name: str, param_type: object, option_type: ApplicationCommandOptionType, required: bool, channel_types:
  list[ChannelType] | None, description: str | None, lookup: Lookup | None, models: tuple[type[LifecycleModel], ...],
  length: Length | None, range: Range | None
- `definition(*, autocomplete: bool) -> ApplicationCommandOption` — Return the option as Discord defines it.
- `argument(interaction: CommandInteraction, value: object, cog: Cog) -> object` — Return the handler argument for the submitted ``value``; ``None`` when the object it names wasn't sent along.

### `class DefinitionOptions(TypedDict, total=False)`
The optional parts of a :class:`CommandDefinition`, as keywords, in any iterable form.

- fields: default_member_permissions: Permissions | None, contexts: Iterable[InteractionContextType] | None, guild_ids:
  Iterable[SnowflakeLike] | None

### `@dataclass class CommandDefinition`
What Discord is told about a command: its name, description, who may use it, where, and in which guilds.

- fields: name: str, description: str, default_member_permissions: Permissions | None, contexts:
  tuple[InteractionContextType, ...] | None, guild_ids: tuple[Snowflake, ...] | None
- `@classmethod of(name: str, description: str, **options: Unpack[DefinitionOptions]) -> Self` — Return the definition of ``name``, holding ``options``' iterables as tuples and its guild ids as snowflakes.

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

### `class CustomIdHandler[I: ComponentInteraction | ModalSubmitInteraction](LoggerMixin)`
A Cog method reached through the prefix of a ``custom_id``: what component and modal handlers share.

- fields: kind: ClassVar[str]
- `custom_id(*args: str | int) -> str` — Build a ``custom_id`` routed to this handler, carrying ``args``.
- `async invoke(cog: Cog, interaction: I, args: Sequence[str]) -> bool` — Call the handler through :data:`~wd_bot.guard.dispatch_guard`; return ``False`` if it raised.

### `class ComponentHandler(CustomIdHandler[ComponentInteraction])`
A Cog method handling every component whose ``custom_id`` starts with :attr:`prefix`.

- attributes: kind

### `class ModalHandler(CustomIdHandler[ModalSubmitInteraction])`
A Cog method handling every modal whose ``custom_id`` starts with :attr:`prefix`.

- attributes: kind

## `wd_bot.extensions` — `wd-bot/src/wd_bot/extensions.py`
Finding, importing, reloading and rolling back the extension modules a bot loads its cogs from.

### `class ExtensionDiscovery`
Lists the modules inside an extensions package, at any depth.

- `modules() -> Generator[str]` — Yield every module (not package) under :attr:`package`, named relative to it.

### `class ExtensionLoader(LoggerMixin)`
Imports a bot's extension modules and builds their cogs; reloads one in place, rolling back on failure.

- `async load_all() -> None` — Load every module in :attr:`package`, recording (not raising) each failure in :attr:`failed`.
- `async load(extension: str) -> None` — Import the module ``extension`` (named relative to :attr:`package`) and add its cogs to the bot.
- `async add_cogs(module: ModuleType) -> None` — Build every concrete :class:`~wd_bot.cogs.Cog` subclass in ``module`` and add it to the bot.
- `async reload(module_name: str) -> set[Scope]` — Re-import the module ``module_name`` and swap its cogs for fresh ones; return the command scopes that changed.

## `wd_bot.guard` — `wd-bot/src/wd_bot/guard.py`
The one guard command, component and listener dispatch run their handler through.

- module names: COMMAND_ERROR_REPLY, ERROR_COLOR, dispatch_guard
- `error_embed(interaction_id: Snowflake) -> Embed` — Return the reply to the interaction ``interaction_id`` whose handler raised.

### `class DispatchGuard(LoggerMixin)`
Runs a handler, turning a refusal or an unexpected exception into the right reply and log entry.

- `async run(handler: str, call: Callable[[], Awaitable[object]], interaction: AnyInteraction | None=None) -> bool` — Await ``call()``, the handler described as ``handler`` (e.g. ``"command 'ping'"``).

## `wd_bot.handlers` — `wd-bot/src/wd_bot/handlers.py`
Which cog methods handle gateway events, component clicks and modal submits: the counterpart of the command registry.

### `class HandlerRegistry(LoggerMixin)`
The ``@Cog.listener`` methods per gateway event, and the ``@Cog.component`` and ``@Cog.modal`` handler per prefix.

- `register(cog: Cog) -> None` — Add ``cog``'s listeners, component handlers and modal handlers.
- `unregister(cog: Cog) -> None` — Remove ``cog``'s listeners, component handlers and modal handlers.
- `listeners(event_name: str) -> Sequence[Listener]` — Return the bound listener methods for the gateway event ``event_name``, in registration order.
- `component(prefix: str) -> tuple[Cog, CustomIdHandler[ComponentInteraction]] | None` — Return the cog and component handler owning the ``custom_id`` prefix ``prefix``, or ``None`` if none does.
- `modal(prefix: str) -> tuple[Cog, CustomIdHandler[ModalSubmitInteraction]] | None` — Return the cog and modal handler owning the ``custom_id`` prefix ``prefix``, or ``None`` if none does.

## `wd_bot.listener` — `wd-bot/src/wd_bot/listener.py`
Runtime `listener()` decorator: tag a Cog method as a gateway dispatch-event listener.

- `listener(name: str | None=None) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]` — Tag a Cog method as a gateway dispatch-event listener.

## `wd_bot.module_tables` — `wd-bot/src/wd_bot/module_tables.py`
The SQLModel tables a module defines, set aside while the module is executed again by a hot reload.

### `@dataclass class ModuleTables`
The tables of a module's table classes, taken out of ``SQLModel.metadata`` so the module can define them again.

- fields: detached: list[Table], present: set[str]
- `@classmethod detach(module_name: str, module: ModuleType | None) -> ModuleTables` — Remove the tables of the classes ``module`` defines from ``SQLModel.metadata``; ``None`` detaches nothing.
- `restore() -> None` — Drop the tables added since :meth:`detach` and put the detached ones back, as before the reload.

## `wd_bot.periodic` — `wd-bot/src/wd_bot/periodic.py`
Periodic tasks: a Cog method the bot runs on an interval for as long as the cog is loaded.

- `type Seconds = float | Callable[[], float]`

### `class PeriodicTask`
A Cog method run every :attr:`seconds` while its cog is loaded, starting right after the cog loads.

- `@property name -> str` — The tick method's name.
- `interval() -> float` — Return the default wait between two ticks, in seconds.
- `start(cog: Cog) -> asyncio.Task[None]` — Start ticking for ``cog`` on its bot's loop; cancel the returned task to stop.

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

## `wd_bot.settings` — `wd-bot/src/wd_bot/settings.py`
wd-bot's settings, backed by their own bot.ini file (operator and internal settings together).

- module names: BOT_CONFIG_FILE

### `class BotConfig[T](Config[T])`
Config descriptor scoped to the bot settings file.

### `class Tokens`
Secrets the operator fills in.

- attributes: discord_token, read_only_token

### `class BotSettings`
How the bot connects to and presents itself on Discord.

- attributes: BOT_SCOPE, intents, permissions, auto_reload_extensions, auto_reload_poll_seconds

## `wd_bot.signature` — `wd-bot/src/wd_bot/signature.py`
Derive a stable signature string for a command's callable, used to detect definition drift.

- `command_signature(func: Callable[..., object]) -> str` — Return a stable string form of ``func``'s signature, used to detect when it has changed.

## `wd_bot.testing` — `wd-bot/src/wd_bot/testing.py`
Test helpers for cogs: build one to call its handlers on, without a running bot.

- `detached_cog[C: Cog](cls: type[C], *, engine: Engine | None=None, **bot: object) -> C` — Return a ``cls`` built without :meth:`Cog.__init <wd_bot.cogs.Cog.__init__>`: no auto-load task, no hot reload.
- `cog_command(func: Callable[..., Awaitable[None]], definition: CommandDefinition, /) -> Command` — Return ``func`` as a :class:`~wd_bot.commands.Command` on a throwaway cog class, built as ``@Cog.command`` builds it.
