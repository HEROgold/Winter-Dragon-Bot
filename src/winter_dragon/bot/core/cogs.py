"""Module that contains Cogs, which are extended classes of discord.ext.commands.Cog/GroupCog."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, NotRequired, Required, Self, TypedDict, Unpack

import discord
from discord import app_commands
from discord.ext import commands
from herogold.log import LoggerMixin
from sqlmodel import Session, select

from winter_dragon.bot.core.app_command_cache import AppCommandCache
from winter_dragon.bot.core.settings import Settings
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.errors.factory import ErrorFactory
from winter_dragon.database.constants import engine
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.disabled_commands import DisabledCommands


if TYPE_CHECKING:
    from discord.ext.commands._types import BotT
    from discord.ext.commands.context import Context

    from winter_dragon.bot.core.bot import WinterDragon


class BotArgs(TypedDict):
    """TypedDict for bot arguments."""

    bot: Required[WinterDragon]
    db_session: NotRequired[Session]


@dataclass(slots=True)
class _ExtensionWatch:
    """Runtime data for tracking an extension file's modification time."""

    path: Path
    task: asyncio.Task[None]
    refs: int
    mtime_ns: int


class Cog(commands.Cog, LoggerMixin):
    """Cog is a subclass of commands.Cog that represents a cog in the WinterDragon bot.

    Args:
    ----
        bot (WinterDragon): The instance of the WinterDragon bot.
        logger (logging.Logger): The logger for the cog.

    """

    bot: WinterDragon
    cache: ClassVar[AppCommandCache]
    has_app_command_mentions: bool = False
    _module_watchers: ClassVar[dict[str, _ExtensionWatch]] = {}

    def __init_subclass__(cls: type[Self], *, auto_load: bool = False) -> None:
        """Automatically load the cog if auto_load is True."""
        super().__init_subclass__()
        cls._should_auto_load = auto_load

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Cog instance.

        Sets up a error handler, app command error handler, and logger for the cog.
        """
        self.bot = kwargs["bot"]
        self.session = kwargs.get("db_session", Session(engine))
        self._auto_reload_module: str | None = None

        if not getattr(Cog, "cache", None):
            Cog.cache = AppCommandCache(self.bot)

        # Expose cache methods on the cog for easier access
        self.get_app_command = Cog.cache.get_app_command
        self.get_command_mention = Cog.cache.get_command_mention

        if not self.has_error_handler():
            # Mention class name from the inheriting subclass.
            self.logger.warning(f"{self.__class__} has no error handler!")
        if not self.has_app_command_error_handler():
            # Mention class name from the inheriting subclass.
            self.logger.warning(f"{self.__class__} has no app command error handler!")

        for listener in self.get_listeners():
            self.logger.debug(listener)

        # Don't start the auto_load loop for the abstract/base Cog classes
        # (we only want concrete subclasses to be able to auto-load themselves).
        if self.__class__ not in (Cog, GroupCog):  # type: ignore[name-defined]
            self.bot.loop.create_task(self.auto_load())
            self._register_auto_reload()

    def is_command_disabled(self, interaction: discord.Interaction) -> bool:
        """Check if a command is disabled for a guild, channel, or user."""
        if interaction.message is None or not isinstance(interaction, commands.Context):
            user = interaction.user
        else:
            user = interaction.message.author

        qual_name = None
        if isinstance(interaction, commands.Context) or interaction.command:
            qual_name = interaction.command.qualified_name
        if not qual_name:
            return False

        user_id = user.id if user else None
        channel_id = interaction.channel.id if interaction.channel else None
        guild_id = interaction.guild.id if interaction.guild else None

        # Check if command is disabled for user, channel, or guild
        statement = (
            select(DisabledCommands)
            .join(Commands)
            .where(
                (Commands.qual_name == qual_name)
                & (
                    (DisabledCommands.target_id == user_id)
                    | (DisabledCommands.target_id == channel_id)
                    | (DisabledCommands.target_id == guild_id)
                ),
            )
        )

        # Return True if any matching disabled command exists
        self.logger.debug(f"Checking if command '{qual_name} is disabled for user {user_id=} {channel_id=} {guild_id=}")
        return self.session.exec(statement).first() is not None

    def is_command_enabled(self, interaction: discord.Interaction) -> bool:
        """Check if a command is enabled for a guild, channel, or user."""
        return not self.is_command_disabled(interaction)

    async def cog_load(self) -> None:
        """When loaded, start the add_mentions and add_disabled_check loops."""
        self.add_mentions.start()
        self.add_disabled_check.start()

    async def auto_load(self) -> None:
        """Load the cog if __cog_auto_load__ is True."""
        self.logger.info(f"Auto-loading Cog {self.__class__.__name__}: {self.__class__._should_auto_load}")  # noqa: SLF001
        if self.__cog_name__ in self.bot.cogs:
            # prevent discord.py from raising an error (simply cleans up logs :) )
            return
        if self.__class__._should_auto_load:  # noqa: SLF001
            await self.bot.add_cog(self)

    def cog_unload(self) -> None:  # type: ignore[override]
        """Stop background loops and unregister any auto-reload watcher."""
        if self.add_mentions.is_running():
            self.add_mentions.stop()
        if self.add_disabled_check.is_running():
            self.add_disabled_check.stop()
        self._deregister_auto_reload()

    @loop(count=1)
    async def add_mentions(self) -> None:
        """Add app command mentions to the bot if it hasn't been done yet."""
        if not self.has_app_command_mentions:
            self.logger.debug(f"Adding app_commands to cache. {Cog.cache=}")
            await Cog.cache.update_app_commands_cache()
            self.has_app_command_mentions = True

    @loop(count=1)
    async def add_disabled_check(self) -> None:
        """Add is_command_disabled check to all commands."""
        for command in chain(self.walk_commands(), self.walk_app_commands()):
            if isinstance(command, app_commands.Group):
                continue
            self.logger.debug(f"Adding is_command_disabled check to {command.qualified_name}")
            command.add_check(self.is_command_enabled)  # type: ignore[reportArgumentType]

    @add_mentions.before_loop
    @add_disabled_check.before_loop
    async def before_loops(self) -> None:
        """Wait until the bot is ready before adding mentions and disabled checks."""
        await self.bot.wait_until_ready()

    # Documentation mentions that `error` is CommandError, however it's type hinted with Exception?
    async def cog_command_error(self, ctx: Context[BotT], error: commands.CommandError) -> None:  # type: ignore[invalid-method-override]
        """Handle errors that occur during command invocation."""
        for handler in ErrorFactory.get_handlers(self.bot, error, ctx=ctx):
            await handler.handle()

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Handle the errors that occur during app command invocation."""
        for handler in ErrorFactory.get_handlers(self.bot, error, interaction=interaction):
            await handler.handle()

    def _register_auto_reload(self) -> None:
        """Start watching the cog's module for file modifications if enabled."""
        if not Settings.auto_reload_extensions:
            return
        module_name = self.__module__
        if not module_name.startswith("winter_dragon.bot.extensions"):
            return
        path = self._resolve_module_path()
        if path is None:
            return
        self._auto_reload_module = module_name
        entry = Cog._module_watchers.get(module_name)
        if entry:
            entry.refs += 1
            return
        task = self.bot.loop.create_task(self._watch_extension_file(module_name))
        Cog._module_watchers[module_name] = _ExtensionWatch(
            path=path,
            task=task,
            refs=1,
            mtime_ns=self._get_file_mtime(path),
        )
        self.logger.debug(f"Enabled auto-reload watcher for {module_name} -> {path}")

    def _resolve_module_path(self) -> Path | None:
        try:
            return Path(inspect.getfile(self.__class__)).resolve()
        except (OSError, TypeError) as exc:
            self.logger.warning(
                "Cannot enable auto-reload for %s because its file path could not be resolved: %s",
                self.__module__,
                exc,
            )
            return None

    def _deregister_auto_reload(self) -> None:
        module_name = self._auto_reload_module
        if module_name is None:
            return
        entry = Cog._module_watchers.get(module_name)
        if entry is None:
            self._auto_reload_module = None
            return
        entry.refs -= 1
        if entry.refs <= 0:
            Cog._module_watchers.pop(module_name, None)
            current_task = None
            try:
                current_task = asyncio.current_task()
            except RuntimeError:
                current_task = None
            if entry.task is not current_task:
                entry.task.cancel()
        self._auto_reload_module = None

    @staticmethod
    def _get_file_mtime(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return 0

    async def _watch_extension_file(self, module_name: str) -> None:
        interval = float(Settings.auto_reload_poll_seconds or 1.5)
        if interval <= 0:
            interval = 1.5
        self.logger.debug(f"Watching {module_name} for changes every {interval}s")
        try:
            while True:
                entry = Cog._module_watchers.get(module_name)
                if entry is None:
                    return
                await asyncio.sleep(interval)
                entry = Cog._module_watchers.get(module_name)
                if entry is None:
                    return
                current_mtime = self._get_file_mtime(entry.path)
                if current_mtime <= entry.mtime_ns:
                    continue
                entry.mtime_ns = current_mtime
                await self._reload_extension(module_name)
                if module_name not in Cog._module_watchers:
                    return
        except asyncio.CancelledError:
            self.logger.debug(f"Stopped watching {module_name} for changes")
            raise
        except Exception:
            self.logger.exception(f"Auto-reload watcher for {module_name} crashed")

    async def _reload_extension(self, module_name: str) -> None:
        self.logger.info(f"Detected change in {module_name}. Reloading extension.")
        try:
            reload_result = self.bot.reload_extension(module_name)
            if inspect.isawaitable(reload_result):
                await reload_result
        except Exception:
            self.logger.exception(f"Failed to reload extension {module_name}")


class GroupCog(Cog):
    """GroupCog is a subclass of Cog that represents a cog with app commands group functionality."""

    # Reflect difference in commands.GroupCog
    __cog_is_app_commands_group__ = True
