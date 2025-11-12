"""Module that contains the WinterDragon bot.

WinterDragon is a subclass of AutoShardedBot from discord.ext.commands.
WinterDragon has additional attributes and methods.
"""
from __future__ import annotations

import datetime
import inspect
import os
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable
from importlib.util import module_from_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

import discord
from discord import Message, app_commands
from discord.ext.commands import AutoShardedBot, CommandError
from discord.ext.commands.bot import BotBase
from discord.ext.commands.errors import ExtensionFailed
from discord.ext.commands.help import DefaultHelpCommand, HelpCommand
from herogold.log import LoggerMixin

from winter_dragon.bot import Settings

from .cogs import Cog
from .config import Config
from .paths import EXTENSIONS, ROOT_DIR


if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import Coroutine
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    from discord.ext.commands.context import Context

type MaybeAwaitable[T] = T | Awaitable[T]
type MaybeAwaitableFunc[**P, T] = Callable[P, MaybeAwaitable[T]]
type _Prefix = Iterable[str] | str
type _PrefixCallable[BotT: BotBase] = MaybeAwaitableFunc[[BotT, Message], _Prefix]
type PrefixType[BotT: BotBase] = _Prefix | _PrefixCallable[BotT]

type BotT[T: BotBase] = T

INTENTS = discord.Intents.none()
INTENTS.members = True
INTENTS.guilds = True
INTENTS.presences = True
INTENTS.guild_messages = True
INTENTS.dm_messages = True
INTENTS.moderation = True
INTENTS.message_content = True
INTENTS.auto_moderation_configuration = True
INTENTS.auto_moderation_execution = True
INTENTS.voice_states = True
GUILD_OWNERSHIP_LIMIT = 0

BOT_PERMISSIONS = 70368744177655 # All bot permissions

OAUTH2 = "https://discord.com/api/oauth2"
DISCORD_AUTHORIZE = f"{OAUTH2}/authorize"

class WinterDragon(AutoShardedBot, LoggerMixin):
    """WinterDragon is a subclass of AutoShardedBot.

    this represents a bot with additional attributes and methods specific to the Winter Dragon bot.
    """

    launch_time: datetime.datetime
    log_saver: Task[Coroutine[Any, Any, None]] | None = None

    def __init__(
        self,
        command_prefix: PrefixType[WinterDragon],
        *,
        help_command: HelpCommand | None = None,
        tree_cls: type[app_commands.CommandTree[Any]] = app_commands.CommandTree,
        description: str | None = None,
        intents: discord.Intents,
        **options: Any,  # We match the type of options as defined in AutoShardedBot  # noqa: ANN401
    ) -> None:
        """Initialize the WinterDragon bot.

        Adds additional attributes and methods to the AutoShardedBot class.
        Like a global app_commands cache and per guild app_commands cache.
        """
        self.launch_time = datetime.datetime.now(datetime.UTC)

        if help_command is None:
            help_command = DefaultHelpCommand()

        super().__init__(
            command_prefix,
            help_command=help_command,
            tree_cls=tree_cls,
            description=description,
            intents=intents,
            **options,
        )

    def get_bot_invite(self) -> str:
        """Get the link to invite the bot to a server."""
        return (
            DISCORD_AUTHORIZE
            + f"?client_id={self.application_id}"
            + f"&permissions={BOT_PERMISSIONS}"
            + f"&scope={"+".join(Settings.BOT_SCOPE)}"
        )

    async def on_error[**P](self, event_method: str, /, *args: P.args, **kwargs: P.kwargs) -> None:
        """Log where errors occur during the event loop."""
        self.logger.exception(f"error in: {event_method}")
        return await super().on_error(event_method, *args, **kwargs)

    async def on_command_error(self, context: Context[BotT], exception: CommandError) -> None:
        """Log where errors occur during command execution."""
        self.logger.exception(f"error in command: {context}", exc_info=exception)
        return await super().on_command_error(context, exception)

    async def get_extensions(self) -> AsyncGenerator[str]:
        """Get all the extensions in the extensions directory. Ignores extensions that start with _."""
        for root, _, files in os.walk(EXTENSIONS):
            for file in files:
                if file.endswith(".py") and not file.startswith("_"):
                    extension = Path(root) / file
                    yield (
                        extension.as_posix()
                        .replace(f"{ROOT_DIR.parent.as_posix()}/", "")
                        .replace("/", ".")
                        .replace(".py", "")
                    )

    @override
    async def _load_from_module_spec(self, spec: ModuleSpec, key: str) -> None:
        """Version that does not check if `def setup` is present."""
        lib = module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)
        except Exception as e:
            del sys.modules[key]
            raise ExtensionFailed(key, e) from e

        try:
            await self._init_cogs(lib)
        except Exception as e:
            del sys.modules[key]
            await self._remove_module_references(lib.__name__)
            await self._call_module_finalizers(lib, key)
            raise ExtensionFailed(key, e) from e
        else:
            self._BotBase__extensions[key] = lib

    async def _init_cogs(self, lib: ModuleType) -> None:
        """Set up a cog by calling its cog_load method if it exists."""
        for obj in lib.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, Cog):
                obj(bot=self)

    async def load_extensions(self) -> None:
        """Load all the extensions in the extensions directory."""
        if not EXTENSIONS.exists():
            self.logger.critical(f"{EXTENSIONS=} not found.")
            return
        self.logger.debug(f"Found {EXTENSIONS=}")
        async for extension in self.get_extensions():
            self.logger.info(f"Loading {extension}")
            try:
                await self.load_extension(extension, package="winter_dragon.bot")
            except Exception:
                self.logger.exception("")
            else:
                self.logger.info(f"Loaded {extension}")

    @Config.with_kwarg("Tokens", "discord_token")
    async def start(self, token: str | None = None, *, reconnect: bool = True, **kwargs: str) -> None:
        """Start the bot with a token from the config file, or a provided token. Provided token takes precedence."""
        token = token or kwargs.get("discord_token")
        if token is None:
            msg = "No token provided"
            raise ValueError(msg)
        return await super().start(token, reconnect=reconnect)
