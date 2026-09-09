"""Module that contains the bot."""

from __future__ import annotations

lazy import asyncio
lazy import datetime
lazy import inspect
lazy import pkgutil
lazy import sys
lazy from importlib.util import find_spec, module_from_spec
lazy from typing import TYPE_CHECKING

lazy from herogold.errors import with_known_exception
lazy from herogold.log import LoggerMixin
lazy from wd_config import Config
lazy from wd_config.bot import Settings
lazy from wd_core.constants import BOT_PERMISSIONS, intents
lazy from wd_discord import Client, GatewayBotInfo
lazy from wd_discord.user import User
lazy from wd_errors.extension import ExtensionError
lazy from wd_errors.startup import StartupError

lazy from .cogs import Cog, GroupCog


if TYPE_CHECKING:
    lazy from collections.abc import AsyncGenerator, Awaitable, Callable
    lazy from importlib.machinery import ModuleSpec
    lazy from types import ModuleType

    lazy from wd_core.intents import Intents
    lazy from wd_discord.models import DiscordModel


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
    cogs: dict[str, Cog]

    def __init__(
        self,
        *,
        intents: Intents = BotConfig.Intents,
        description: str | None = None,
    ) -> None:
        """Initialize the Bot with the given intents and an optional description."""
        self.launch_time = datetime.datetime.now(datetime.UTC)
        self.intents = intents
        self.description = description
        self.cogs = {}
        self._extensions: dict[str, ModuleType] = {}
        self._listeners: dict[str, list[Callable[..., Awaitable[None]]]] = {}

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
        await cog.load()

    async def _dispatch(self, event_name: str, payload: DiscordModel) -> None:
        """Fan out a parsed gateway dispatch event to every registered listener for it."""
        for handler in self._listeners.get(event_name, []):
            self.loop.create_task(self._invoke_listener(handler, payload))

    async def _invoke_listener(self, handler: Callable[..., Awaitable[None]], payload: DiscordModel) -> None:
        try:
            await handler(payload)
        except Exception:
            self.logger.exception(t"Unhandled exception in listener {handler!r} for {payload!r}")

    def _discover_wd_cogs_modules(self) -> list[str]:
        """Discover all modules in the wd_cogs package recursively."""
        modules = []
        try:
            import wd_cogs  # noqa: PLC0415

            # Recursively walk through all packages and modules in wd_cogs
            def walk_packages(package: ModuleType, prefix: str = "") -> None:
                """Recursively walk through packages and collect module names."""
                package_path = package.__path__  # type: ignore[attr-defined]
                for _importer, mod_name, is_package in pkgutil.walk_packages(
                    path=package_path,
                    prefix=f"{prefix}{package.__name__}.",
                ):
                    if not is_package and not mod_name.endswith(".__init__"):
                        modules.append(mod_name)

            walk_packages(wd_cogs)
        except ImportError:
            self.logger.warning(t"wd_cogs package not found, skipping cog discovery")
        except Exception:
            self.logger.exception(t"Error discovering wd_cogs modules")

        return modules

    async def get_extensions(self) -> AsyncGenerator[str]:
        """Get all extensions from the wd_cogs package.

        Automatically discovers all .py modules in wd_cogs regardless of structure.
        """
        for module in self._discover_wd_cogs_modules():
            yield module

    async def _init_cogs(self, lib: ModuleType) -> None:
        """Instantiate every concrete Cog subclass found in a loaded extension module."""
        for obj in lib.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, Cog) and obj not in (Cog, GroupCog):
                obj(bot=self)

    async def _load_from_module_spec(self, spec: ModuleSpec, key: str) -> None:
        """Execute a module spec and instantiate its cogs."""
        if spec.loader is None:
            raise ExtensionError(key, RuntimeError("Module spec has no loader"))

        module = module_from_spec(spec)
        sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
            await self._init_cogs(module)
        except Exception as e:
            del sys.modules[key]
            raise ExtensionError(key, e) from e

        self._extensions[key] = module

    async def load_extension(self, extension: str) -> None:
        """Load a single extension from the wd_cogs package."""
        spec = find_spec(f"wd_cogs.{extension}")
        if not spec:
            raise ExtensionError(extension, RuntimeError("Extension not found"))
        await self._load_from_module_spec(spec, extension)

    async def load_extensions(self) -> None:
        """Load all cogs from the wd_cogs package."""
        self.logger.debug(t"Starting to load cogs from wd_cogs")
        async for extension in self.get_extensions():
            self.logger.info(t"Loading cog {extension}")
            try:
                await self.load_extension(extension)
            except Exception:
                self.logger.exception(t"Failed to load cog {extension}")
            else:
                self.logger.info(t"Loaded cog {extension}")

    @with_known_exception(StartupError)
    @Config.with_kwarg("Tokens", "discord_token")
    async def start(self, token: str) -> None:
        """Start the bot with a token from the config file, or a provided token. Provided token takes precedence."""
        self.loop = asyncio.get_running_loop()
        async with Client(token) as client:
            me = await client.get_current_user()
            if not isinstance(me, User):
                msg = "Failed to get current user from Discord API"
                raise StartupError(msg)

            gw_info = await client.get_gateway_bot()
            if not isinstance(gw_info, GatewayBotInfo):
                msg = "Failed to get gateway bot info from Discord API"
                raise StartupError(msg)

            manager = await client.get_shard_manager(gw_info, intents=self.intents)
            await self.load_extensions()
            async with manager:
                self.logger.info(t"Bot is running with {len(manager.shards)} shards")
                await manager.serve_forever(self._dispatch)
