"""Module that contains the bot."""

lazy import asyncio
lazy from typing import TYPE_CHECKING

lazy import wd_cogs
lazy from herogold.errors import with_known_exception
lazy from herogold.log import LoggerMixin
lazy from wd_config import OperatorFiles
lazy from wd_config.discord import URLS
lazy from wd_discord import (
    AutocompleteInteraction,
    Client,
    CommandInteraction,
    ComponentInteraction,
    GatewayBotInfo,
    ModalSubmitInteraction,
    Token,
    is_network_error,
)
lazy from wd_discord.intents import Intents
lazy from wd_discord.permissions import Permissions
lazy from wd_errors.startup import StartupError
lazy from wd_types.clock import utc_now

lazy from wd_bot.application import ApplicationId
lazy from wd_bot.auto_sync import CommandSyncer
lazy from wd_bot.components import parse_custom_id
lazy from wd_bot.extensions import ExtensionLoader
lazy from wd_bot.guard import dispatch_guard
lazy from wd_bot.handlers import HandlerRegistry
lazy from wd_bot.registry import CommandRegistry

lazy from .settings import BotConfig, BotSettings


if TYPE_CHECKING:
    lazy import datetime
    lazy from collections.abc import Awaitable, Callable, Generator, Iterable
    lazy from types import ModuleType

    lazy from wd_discord import AnyInteraction
    lazy from wd_discord.gateway.sharding import ShardManager
    lazy from wd_discord.models import DiscordModel
    lazy from wd_discord.snowflake import Snowflake

    lazy from wd_bot.cogs import Cog
    lazy from wd_bot.commands import AppCommand
    lazy from wd_bot.components import CustomIdHandler
    lazy from wd_bot.registry import Scope


def invite_url() -> str:
    """Return the link to invite the bot to a server, with the scopes and permissions in ``bot.ini``.

    Raises:
        RuntimeError: :meth:`ApplicationId.load` hasn't run in this process.

    """
    scope = "%20".join(BotSettings.BOT_SCOPE)
    permissions = Permissions(BotSettings.permissions)
    return f"{URLS().oauth2_authorize}?client_id={ApplicationId.get()}&permissions={int(permissions)}&scope={scope}"


class Bot(LoggerMixin):
    """A forever-running Discord bot: connects to the gateway, loads extensions, dispatches events.

    Bot wires its collaborators together and runs the lifecycle: :attr:`registry` holds the commands,
    :attr:`handlers` the listeners and component handlers, and :attr:`extensions` imports and reloads the
    modules the cogs come from.
    """

    launch_time: datetime.datetime
    loop: asyncio.AbstractEventLoop
    client: Client
    cogs: dict[str, Cog]

    def __init__(
        self,
        *,
        intents: Intents | None = None,
        description: str | None = None,
        extensions_package: ModuleType = wd_cogs,
    ) -> None:
        """Initialize the Bot with the given intents (default: ``BotSettings.intents``) and an optional description.

        ``extensions_package`` is the package :attr:`extensions` discovers cogs from -
        defaults to the shared ``wd_cogs`` catalog, but a bot built on its own cog package
        (e.g. ``winter_dragon.cogs``) can point discovery at that instead.
        """
        self.launch_time = utc_now()
        self.intents = Intents(BotSettings.intents) if intents is None else intents
        self.description = description
        self.cogs = {}
        self.shard_manager: ShardManager | None = None
        """The gateway shards while :meth:`start` runs; ``None`` before they connect and after they close."""
        self.handlers = HandlerRegistry()
        """The listeners per gateway event and the component handler per ``custom_id`` prefix."""
        self.extensions = ExtensionLoader(self, extensions_package)
        """Imports, reloads and rolls back the extension modules in ``extensions_package``."""
        self.registry = CommandRegistry()
        """The registered commands per scope, and the IDs Discord gave them."""
        self.syncer = CommandSyncer(self.registry)
        """Pushes :attr:`registry` changes to Discord."""

    async def add_cog(self, cog: Cog) -> None:
        """Register a cog's commands, listeners and component handlers, load it, then start its periodic tasks.

        Raises :class:`TypeError` when a handler expects a guild interaction its command or cog wouldn't give it.
        """
        type(cog).check_guild_handlers()
        self.cogs[cog.__cog_name__] = cog
        self.registry.register(cog)
        self.handlers.register(cog)
        await cog.load()
        cog.start_periodic_tasks()

    async def remove_cog(self, cog: Cog) -> set[Scope]:
        """Unregister ``cog``'s handlers, stop its periodic tasks and unload it; return the command scopes that changed."""
        self.cogs.pop(cog.__cog_name__, None)
        self.handlers.unregister(cog)
        scopes = self.registry.unregister(cog)
        await cog.stop_periodic_tasks()
        await cog.unload()
        return scopes

    async def _dispatch_interaction(self, interaction: AnyInteraction) -> None:
        """Route a command, component or autocomplete interaction to its registered handler.

        A command or component handler that refused or raised is answered by :data:`~wd_bot.guard.dispatch_guard`, so an
        interaction never goes unanswered. A failed autocomplete has no message to reply with: the user just sees no
        suggestions.
        """
        match interaction:
            case CommandInteraction():
                await self._dispatch_command(interaction)
            case ComponentInteraction():
                await self._dispatch_component(interaction)
            case ModalSubmitInteraction():
                await self._dispatch_modal(interaction)
            case AutocompleteInteraction():
                await self._dispatch_autocomplete(interaction)
            case _:
                return

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
        return await self._dispatch_custom_id(interaction, self.handlers.component, "component")

    async def _dispatch_modal(self, interaction: ModalSubmitInteraction) -> bool:
        """Invoke the handler owning the submitted modal's ``custom_id`` prefix; ``False`` only if it raised."""
        return await self._dispatch_custom_id(interaction, self.handlers.modal, "modal")

    async def _dispatch_custom_id[I: ComponentInteraction | ModalSubmitInteraction](
        self,
        interaction: I,
        registry: Callable[[str], tuple[Cog, CustomIdHandler[I]] | None],
        kind: str,
    ) -> bool:
        """Invoke the handler ``registry`` returns for the ``custom_id`` prefix; ``False`` only if it raised."""
        prefix, args = parse_custom_id(interaction.custom_id)
        entry = registry(prefix)
        if entry is None:
            self.logger.warning(t"No registered {kind} handler for custom_id {interaction.custom_id!r}")
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
        allow_writes = not self.extensions.failed and any(True for _ in self.registry.commands())
        await self.syncer.sync(client, self.registry.scopes() if scopes is None else scopes, allow_writes=allow_writes)

    async def _startup_sync(self, client: Client) -> None:
        """Run the startup :meth:`sync_commands`, logging (not raising) any failure so the gateway still starts."""
        try:
            await self.sync_commands(client)
        except Exception:
            self.logger.exception(t"Startup command sync failed; continuing without it")

    async def _dispatch(self, event_name: str, payload: DiscordModel) -> None:
        """Let the client take a parsed gateway dispatch, then fan the bound event out to every listener for it.

        :meth:`Client.receive <wd_discord.client.Client.receive>` updates the client's cache first, so listeners
        read state that already includes the event.

        An interaction is also routed to its command or component handler.
        """
        event = self.client.receive(payload).event
        if isinstance(event, CommandInteraction | ComponentInteraction | ModalSubmitInteraction):
            self.loop.create_task(self._dispatch_interaction(event))
        for handler in self.handlers.listeners(event_name):
            self.loop.create_task(self._invoke_listener(handler, event))

    async def _invoke_listener(self, handler: Callable[..., Awaitable[None]], payload: object) -> None:
        """Run the listener ``handler`` on ``payload`` through :data:`~wd_bot.guard.dispatch_guard`."""
        await dispatch_guard.run(f"listener '{handler.__qualname__}'", lambda: handler(payload))

    async def reload_extension(self, module_name: str) -> None:
        """Reload the extension module ``module_name`` via :attr:`extensions`, then sync the command scopes it changed.

        A failed reload keeps the old cogs and raises :class:`~wd_errors.extension.ExtensionError`; nothing is synced.
        """
        scopes = await self.extensions.reload(module_name)
        await self.sync_commands(self.client, scopes)

    async def _fetch_gateway_info(self, client: Client) -> GatewayBotInfo:
        """Check the token works, learn the application ID, then fetch the gateway info.

        Raises :class:`StartupError` if any call fails.
        """
        me = await client.users.me()
        if is_network_error(me):
            msg = "Failed to get current user from Discord API"
            raise StartupError(msg)
        await ApplicationId.load(client)
        gw_info = await client.get_gateway_bot()
        if not isinstance(gw_info, GatewayBotInfo):
            msg = "Failed to get gateway bot info from Discord API"
            raise StartupError(msg)
        return gw_info

    @with_known_exception(StartupError)
    @BotConfig.with_kwarg("Tokens", "discord_token", name="token")
    async def start(self, token: str) -> None:
        """Start the bot with the token from bot.ini.

        Raises :class:`~wd_config.errors.FirstTimeLaunchError` before connecting while any operator file
        still holds a ``!!`` value.
        """
        OperatorFiles.check()
        self.loop = asyncio.get_running_loop()
        async with Client(Token(token)) as client:
            self.client = client
            gw_info = await self._fetch_gateway_info(client)
            manager = await client.get_shard_manager(gw_info, intents=self.intents)
            await self.extensions.load_all()
            await self._startup_sync(client)
            async with manager:
                self.shard_manager = manager
                self.logger.info(t"Bot is running with {len(manager.shards)} shards")
                try:
                    await manager.serve_forever(self._dispatch)
                finally:
                    self.shard_manager = None


def _guild_id(interaction: AnyInteraction) -> Snowflake | None:
    """Return the ID of the guild ``interaction`` came from, or ``None`` in a DM."""
    guild = interaction.guild
    return None if guild is None else guild.id
