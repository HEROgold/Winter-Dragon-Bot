"""Module that contains the bot."""

from __future__ import annotations

import datetime
import inspect
import pkgutil
import sys
from importlib.util import find_spec, module_from_spec
from typing import TYPE_CHECKING, Any

from herogold.errors import with_known_exception
from herogold.log import LoggerMixin
from wd_config import Config
from wd_config.bot import Settings
from wd_core.command import CommandTree
from wd_core.constants import BOT_PERMISSIONS, intents
from wd_core.intents import Intents
from wd_discord import Client, GatewayBotInfo
from wd_discord.user import User
from wd_errors.extension import ExtensionError
from wd_errors.startup import StartupError

from wd_bot.help import DefaultHelpCommand, HelpCommand, default_help

from .cogs import Cog


if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import AsyncGenerator, Coroutine
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    from wd_types.alias import Bot, PrefixType

class BotConfig:
    """Basic bot configuration values."""

    Intents = Config(intents)
    Permissions = Config(BOT_PERMISSIONS)

class MissingError(Exception):
    """Raised when a required attribute is missing."""

class Bot(LoggerMixin):
    """Bot is a subclass of AutoShardedBot.

    this represents a bot with additional attributes and methods specific to the Winter Dragon bot.
    """

    launch_time: datetime.datetime
    log_saver: Task[Coroutine[Any, Any, None]] | None = None

    def __init__(
        self,
        command_prefix: PrefixType[Bot],
        *,
        help_command: HelpCommand = default_help,
        tree_cls: type[CommandTree[Any]] = CommandTree,
        description: str | None = None,
        intents: Intents = BotConfig.Intents,
    ) -> None:
        """Initialize the Bot bot.

        Adds additional attributes and methods to the AutoShardedBot class.
        Like a global app_commands cache and per guild app_commands cache.
        """
        self.launch_time = datetime.datetime.now(datetime.UTC)

        # TODO; copy from discord.py's bot.__init__, but use our own
        # intents, permissions, and Client setup.
        super().__init__(
            command_prefix,
            help_command=help_command,
            tree_cls=tree_cls,
            description=description,
            intents=intents,
        )

    def get_bot_invite(self) -> str:
        """Get the link to invite the bot to a server."""
        if not self.application_id:
            msg = "Bot application ID is not set."
            raise ValueError(msg)
        return discord.utils.oauth_url(
            self.application_id,
            permissions=BotConfig.Permissions,
            scopes=Settings.BOT_SCOPE,
        )

    async def on_error[**P](self, event_method: str, /, *args: P.args, **kwargs: P.kwargs) -> None:
        """Log where errors occur during the event loop."""
        self.logger.error(t"error in: {event_method}")
        return await super().on_error(event_method, *args, **kwargs)

    async def on_command_error(self, context: Context[Bot], exception: CommandError) -> None:
        """Log where errors occur during command execution."""
        self.logger.error(t"error in command: {context}", exc_info=exception)
        return await super().on_command_error(context, exception)

    def _discover_wd_cogs_modules(self) -> list[str]:
        """Discover all modules in the wd_cogs package recursively."""
        modules = []
        try:
            import wd_cogs  # noqa: F401, PLC0415

            # Recursively walk through all packages and modules in wd_cogs
            def walk_packages(package: ModuleType, prefix: str = "") -> None:
                """Recursively walk through packages and collect module names."""
                package_path = package.__path__  # type: ignore[attr-defined]
                for _importer, mod_name, is_package in pkgutil.walk_packages(
                    path=package_path, prefix=f"{prefix}{package.__name__}.",
                ):
                    if not is_package and not mod_name.endswith(".__init__"):
                        modules.append(mod_name)

            import wd_cogs as wd_cogs_module  # noqa: PLC0415

            walk_packages(wd_cogs_module)
        except ImportError:
            self.logger.warning("wd_cogs package not found, skipping cog discovery")
        except Exception:
            self.logger.exception("Error discovering wd_cogs modules")

        return modules

    async def get_extensions(self) -> AsyncGenerator[str]:
        """Get all extensions from the wd_cogs package.

        Automatically discovers all .py modules in wd_cogs regardless of structure.
        """
        for module in self._discover_wd_cogs_modules():
            yield module

    async def _load_from_module_spec(self, spec: ModuleSpec, key: str) -> None:
        """Version that does not check if `def setup` is present."""
        lib = module_from_spec(spec)
        sys.modules[key] = lib
        if spec.loader is None:
            del sys.modules[key]
            raise ExtensionError(key, RuntimeError("Module spec has no loader"))

        try:
            spec.loader.exec_module(lib)
        except Exception as e:
            del sys.modules[key]
            raise ExtensionError(key, e) from e

        try:
            await self._init_cogs(lib)
        except Exception as e:
            del sys.modules[key]
            await self._remove_module_references(lib.__name__)
            await self._call_module_finalizers(lib, key)
            raise ExtensionError(key, e) from e
        else:
            # Store the loaded extension in the mangled __extensions attribute
            # This is required, because discord.py _load_from_module_spec is internal
            # And we want to change how extensions are loaded without calling setup()
            # we use auto_load on Cogs to initialize them
            extensions = getattr(self, "_BotBase__extensions", None)
            if not isinstance(extensions, dict):
                msg = "Bot extension registry is unavailable"
                raise MissingError(msg)
            extensions[key] = lib

    async def _init_cogs(self, lib: ModuleType) -> None:
        """Set up a cog by calling its cog_load method if it exists."""
        for obj in lib.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, Cog):
                obj(bot=self)

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
        async with Client(token) as client:
            me = await client.get_current_user()
            if not isinstance(me, User):
                msg = "Failed to get current user from Discord API"
                raise StartupError(msg)

            gw_info = await client.get_gateway_bot()
            if not isinstance(gw_info, GatewayBotInfo):
                msg = "Failed to get gateway bot info from Discord API"
                raise StartupError(msg)

            manager = await client.get_shard_manager(gw_info)
            async with manager:
                self.logger.info(t"Bot is running with {len(manager.shards)} shards")
                # TODO: keep connection alive for every shard.
                # Currently, the bot simply starts up and then exits
                # If we want this to be functional, loaded extensions/cogs
                # Should be able to respond to events from the gateway, and the bot should stay alive until manually stopped.
