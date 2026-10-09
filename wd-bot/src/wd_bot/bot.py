"""Module that contains the bot."""

from __future__ import annotations

lazy import asyncio
lazy import datetime
lazy import inspect
lazy import sys
lazy from importlib.util import find_spec, module_from_spec
lazy from typing import TYPE_CHECKING

lazy import wd_cogs
lazy from herogold.errors import with_known_exception
lazy from herogold.log import LoggerMixin
lazy from wd_config import Config
lazy from wd_config.bot import Settings
lazy from wd_core.constants import BOT_PERMISSIONS, intents
lazy from wd_discord import (
    AutocompleteInteraction,
    Client,
    CommandInteraction,
    ComponentInteraction,
    GatewayBotInfo,
    bind,
    is_network_error,
)
lazy from wd_errors.extension import ExtensionError
lazy from wd_errors.startup import StartupError

lazy from wd_bot.auto_sync import CommandSyncer
lazy from wd_bot.components import parse_custom_id
lazy from wd_bot.extensions import ExtensionDiscovery
lazy from wd_bot.registry import CommandRegistry

lazy from .cogs import Cog, GroupCog


if TYPE_CHECKING:
    lazy from collections.abc import AsyncGenerator, Awaitable, Callable, Generator, Iterable
    lazy from importlib.machinery import ModuleSpec
    lazy from types import ModuleType

    lazy from wd_core.intents import Intents
    lazy from wd_discord import AnyInteraction
    lazy from wd_discord.models import DiscordModel
    lazy from wd_discord.snowflake import Snowflake

    lazy from wd_bot.commands import AppCommand
    lazy from wd_bot.components import ComponentHandler
    lazy from wd_bot.registry import Scope


COMMAND_ERROR_REPLY = "Something went wrong running this command."
"""Ephemeral reply sent when a command handler raises."""


class BotConfig:
    """Basic bot configuration values."""

    Intents = Config(intents)
    Permissions = Config(BOT_PERMISSIONS)


class MissingError(Exception):
    """Raised when a required attribute is missing."""


class Bot(LoggerMixin):
    """A forever-running Discord bot: connects to the gateway, loads extensions, dispatches events.

    Built entirely on wd-* packages (wd_discord, wd_core, wd_config) - no discord.py.
    """

    launch_time: datetime.datetime
    loop: asyncio.AbstractEventLoop
    client: Client
    cogs: dict[str, Cog]

    def __init__(
        self,
        *,
        intents: Intents = BotConfig.Intents,
        description: str | None = None,
        extensions_package: ModuleType = wd_cogs,
    ) -> None:
        """Initialize the Bot with the given intents and an optional description.

        ``extensions_package`` is the package :meth:`load_extensions` discovers cogs from -
        defaults to the shared ``wd_cogs`` catalog, but a bot built on its own cog package
        (e.g. ``winter_dragon.cogs``) can point discovery at that instead.
        """
        self.launch_time = datetime.datetime.now(datetime.UTC)
        self.intents = intents
        self.description = description
        self.extensions_package = extensions_package
        self.cogs = {}
        self._extensions: dict[str, ModuleType] = {}
        self._failed_extensions: set[str] = set()
        self._listeners: dict[str, list[Callable[..., Awaitable[None]]]] = {}
        self._components: dict[str, tuple[Cog, ComponentHandler]] = {}
        self.registry = CommandRegistry()
        """The registered commands per scope, and the IDs Discord gave them."""
        self.syncer = CommandSyncer(self.registry)
        """Pushes :attr:`registry` changes to Discord."""

    def get_bot_invite(self) -> str:
        """Get the link to invite the bot to a server."""
        if not Settings.application_id:
            msg = "Settings.application_id is not configured."
            raise ValueError(msg)
        scope = "%20".join(Settings.BOT_SCOPE)
        return (
            "https://discord.com/api/oauth2/authorize"
            f"?client_id={Settings.application_id}&permissions={int(BotConfig.Permissions)}&scope={scope}"
        )

    async def add_cog(self, cog: Cog) -> None:
        """Register a cog and any of its @Cog.listener()-tagged methods."""
        self.cogs[cog.__cog_name__] = cog
        for _, member in inspect.getmembers(cog, predicate=inspect.iscoroutinefunction):
            event = getattr(member, "__listener_event__", None)
            if event:
                self._listeners.setdefault(event, []).append(member)
        self.registry.register(cog)
        for handler in cog.components():
            if (existing_handler := self._components.get(handler.prefix)) is not None and existing_handler[0] is not cog:
                previous = existing_handler[0].__cog_name__
                self.logger.warning(
                    t"Duplicate component prefix '{handler.prefix}': cog '{cog.__cog_name__}' replaces '{previous}'",
                )
            self._components[handler.prefix] = (cog, handler)
        await cog.load()

    async def remove_cog(self, cog: Cog) -> set[Scope]:
        """Unregister ``cog``'s listeners, commands and components and unload it; return the command scopes that changed."""
        self.cogs.pop(cog.__cog_name__, None)
        for handlers in self._listeners.values():
            handlers[:] = [handler for handler in handlers if getattr(handler, "__self__", None) is not cog]
        for prefix in [prefix for prefix, (owner, _) in self._components.items() if owner is cog]:
            del self._components[prefix]
        scopes = self.registry.unregister(cog)
        await cog.unload()
        return scopes

    async def _dispatch_interaction(self, interaction: AnyInteraction) -> None:
        """Route a command, component or autocomplete interaction to its registered handler.

        If a command or component handler raised, the user gets an ephemeral error reply, so an interaction never goes
        unanswered. A failed autocomplete has no message to reply with: the user just sees no suggestions.
        """
        match interaction:
            case CommandInteraction():
                succeeded = await self._dispatch_command(interaction)
            case ComponentInteraction():
                succeeded = await self._dispatch_component(interaction)
            case AutocompleteInteraction():
                await self._dispatch_autocomplete(interaction)
                return
            case _:
                return
        if not succeeded:
            await interaction.respond(COMMAND_ERROR_REPLY, ephemeral=True)

    async def _dispatch_command(self, interaction: CommandInteraction) -> bool:
        """Invoke the command ``interaction`` names; ``False`` only if its handler raised."""
        entry = self.registry.entry(interaction.command_name, _guild_id(interaction))
        if entry is None:
            self.logger.warning(t"No registered command for interaction {interaction.command_name!r}")
            return True
        return await entry.command.invoke(entry.cog, interaction)

    async def _dispatch_autocomplete(self, interaction: AutocompleteInteraction) -> bool:
        """Suggest values for the option being typed in the command ``interaction`` names; ``False`` if that failed."""
        entry = self.registry.entry(interaction.command_name, _guild_id(interaction))
        if entry is None:
            self.logger.warning(t"No registered command for autocomplete {interaction.command_name!r}")
            return False
        return await entry.command.complete(entry.cog, interaction)

    async def _dispatch_component(self, interaction: ComponentInteraction) -> bool:
        """Invoke the handler owning the clicked component's ``custom_id`` prefix; ``False`` only if it raised."""
        prefix, args = parse_custom_id(interaction.custom_id)
        entry = self._components.get(prefix)
        if entry is None:
            self.logger.warning(t"No registered component handler for custom_id {interaction.custom_id!r}")
            return True
        cog, handler = entry
        return await handler.invoke(cog, interaction, args)

    @property
    def commands(self) -> Generator[AppCommand]:
        """Yield every registered top-level command (plain commands and subcommand groups)."""
        yield from self.registry.commands()

    async def sync_commands(self, client: Client, scopes: Iterable[Scope] | None = None) -> None:
        """Sync ``scopes`` (default: every scope the registry knows) to Discord via :attr:`syncer`.

        Writes are suppressed while any extension failed to load, or when no command is registered at all: a
        PUT replaces a scope's whole list, so the missing commands would be deleted from Discord. The scopes
        are still read, so command IDs are recovered either way.
        """
        allow_writes = not self._failed_extensions and any(True for _ in self.registry.commands())
        await self.syncer.sync(client, self.registry.scopes() if scopes is None else scopes, allow_writes=allow_writes)

    async def _startup_sync(self, client: Client) -> None:
        """Run the startup :meth:`sync_commands`, logging (not raising) any failure so the gateway still starts."""
        try:
            await self.sync_commands(client)
        except Exception:
            self.logger.exception(t"Startup command sync failed; continuing without it")

    async def _dispatch(self, event_name: str, payload: DiscordModel) -> None:
        """Bind a parsed gateway dispatch event to the client, then fan it out to every registered listener for it.

        An interaction is also routed to its command or component handler.
        """
        event = bind(self.client, payload)
        if isinstance(event, CommandInteraction | ComponentInteraction):
            self.loop.create_task(self._dispatch_interaction(event))
        for handler in self._listeners.get(event_name, []):
            self.loop.create_task(self._invoke_listener(handler, event))

    async def _invoke_listener(self, handler: Callable[..., Awaitable[None]], payload: object) -> None:
        try:
            await handler(payload)
        except Exception:
            self.logger.exception(t"Unhandled exception in listener {handler!r} for {payload!r}")

    def _discover_extension_modules(self) -> list[str]:
        """Discover all modules in :attr:`extensions_package` recursively.

        Names are relative to :attr:`extensions_package` (e.g. ``"heartbeat"``, not
        ``"winter_dragon.cogs.heartbeat"``) - :meth:`load_extension` prepends the package
        itself, so a returned name must not already include it. A discovery failure is recorded in
        ``_failed_extensions`` (under the package's name), so :meth:`sync_commands` won't delete.
        """
        try:
            return list(ExtensionDiscovery(self.extensions_package).modules())
        except ImportError:
            self._failed_extensions.add(self.extensions_package.__name__)
            self.logger.warning(t"{self.extensions_package.__name__} package not found, skipping cog discovery")
        except Exception:
            self._failed_extensions.add(self.extensions_package.__name__)
            self.logger.exception(t"Error discovering {self.extensions_package.__name__} modules")
        return []

    async def get_extensions(self) -> AsyncGenerator[str]:
        """Get all extensions from :attr:`extensions_package`.

        Automatically discovers all .py modules in that package regardless of structure.
        """
        for module in self._discover_extension_modules():
            yield module

    async def _init_cogs(self, lib: ModuleType) -> None:
        """Instantiate every concrete Cog subclass found in a loaded extension module."""
        for obj in lib.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, Cog) and obj not in (Cog, GroupCog):
                cog = obj(bot=self)
                # Register now rather than relying on the task Cog.__init__ scheduled: sync_commands
                # runs right after load_extensions and must see every command. auto_load is idempotent.
                await cog.auto_load()

    async def _load_from_module_spec(self, spec: ModuleSpec, key: str) -> None:
        """Import a module spec under its full name and instantiate its cogs.

        A module another extension already imported is reused, not executed again: a second copy would
        redefine its classes, which e.g. SQLModel tables don't allow.
        """
        if spec.loader is None:
            raise ExtensionError(key, RuntimeError("Module spec has no loader"))

        module = sys.modules.get(spec.name)
        if module is None:
            module = module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                del sys.modules[spec.name]
                raise ExtensionError(key, e) from e
        try:
            await self._init_cogs(module)
        except Exception as e:
            raise ExtensionError(key, e) from e

        self._extensions[key] = module

    async def reload_extension(self, module_name: str) -> None:
        """Re-import the extension module ``module_name``, swap its cogs for fresh ones and sync what changed.

        The new code is imported before anything is unregistered, so if it fails to import, or its cogs fail to
        build, the old cogs stay registered and the error is raised.
        """
        old_module = sys.modules.get(module_name)
        spec = find_spec(module_name)
        if spec is None or spec.loader is None:
            raise ExtensionError(module_name, RuntimeError("Extension not found"))
        module = module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ExtensionError(module_name, e) from e

        old_cogs = self._cogs_from(module_name)
        scopes: set[Scope] = set()
        for cog in old_cogs:
            scopes |= await self.remove_cog(cog)
        sys.modules[module_name] = module
        try:
            await self._init_cogs(module)
        except Exception as e:
            for cog in self._cogs_from(module_name):
                await self.remove_cog(cog)
            if old_module is not None:
                sys.modules[module_name] = old_module
            for cog in old_cogs:
                await self.add_cog(cog)
            raise ExtensionError(module_name, e) from e
        for cog in self._cogs_from(module_name):
            scopes |= self.registry.scopes_of(cog)
        self.logger.info(t"Reloaded extension {module_name}")
        await self.sync_commands(self.client, scopes)

    def _cogs_from(self, module_name: str) -> list[Cog]:
        """Return the loaded cogs whose class is defined in the module ``module_name``."""
        return [cog for cog in self.cogs.values() if type(cog).__module__ == module_name]

    async def load_extension(self, extension: str) -> None:
        """Load a single extension from :attr:`extensions_package`."""
        spec = find_spec(f"{self.extensions_package.__name__}.{extension}")
        if not spec:
            raise ExtensionError(extension, RuntimeError("Extension not found"))
        await self._load_from_module_spec(spec, extension)
        self._failed_extensions.discard(extension)

    async def load_extensions(self) -> None:
        """Load all cogs from :attr:`extensions_package`."""
        self.logger.debug(t"Starting to load cogs from {self.extensions_package.__name__}")
        self._failed_extensions.clear()
        async for extension in self.get_extensions():
            self.logger.info(t"Loading cog {extension}")
            try:
                await self.load_extension(extension)
            except Exception:
                self._failed_extensions.add(extension)
                self.logger.exception(t"Failed to load cog {extension}")
            else:
                self.logger.info(t"Loaded cog {extension}")

    async def _fetch_gateway_info(self, client: Client) -> GatewayBotInfo:
        """Check the token works, then fetch the gateway info; raise :class:`StartupError` if either call fails."""
        me = await client.users.me()
        if is_network_error(me):
            msg = "Failed to get current user from Discord API"
            raise StartupError(msg)
        gw_info = await client.get_gateway_bot()
        if not isinstance(gw_info, GatewayBotInfo):
            msg = "Failed to get gateway bot info from Discord API"
            raise StartupError(msg)
        return gw_info

    @with_known_exception(StartupError)
    @Config.with_kwarg("Tokens", "discord_token", name="token")
    async def start(self, token: str) -> None:
        """Start the bot with a token from the config file, or a provided token. Provided token takes precedence."""
        self.loop = asyncio.get_running_loop()
        async with Client(token) as client:
            self.client = client
            gw_info = await self._fetch_gateway_info(client)
            manager = await client.get_shard_manager(gw_info, intents=self.intents)
            await self.load_extensions()
            await self._startup_sync(client)
            async with manager:
                self.logger.info(t"Bot is running with {len(manager.shards)} shards")
                await manager.serve_forever(self._dispatch)


def _guild_id(interaction: AnyInteraction) -> Snowflake | None:
    """Return the ID of the guild ``interaction`` came from, or ``None`` in a DM."""
    guild = interaction.guild
    return None if guild is None else guild.id
