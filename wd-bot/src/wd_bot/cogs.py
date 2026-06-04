"""Module that contains Cogs, which are extended classes of discord.ext.commands.Cog/GroupCog."""

from __future__ import annotations

from enum import IntFlag, auto
from typing import TYPE_CHECKING, ClassVar, NotRequired, Required, Self, TypedDict, Unpack

from discord.ext import commands
from discord.ext.commands.cog import _cog_special_method
from herogold.log import LoggerMixin
from sqlmodel import Session
from wd_db.constants import engine
from wd_errors.factory import ErrorFactory

from wd_bot.auto_reload import AutoReloadWatcher
from wd_bot.cache import AppCommandCache
from wd_bot.tasks import loop


if TYPE_CHECKING:
    import discord
    from discord import app_commands
    from discord.ext.commands._types import BotT
    from discord.ext.commands.context import Context

    from wd_bot.bot import WinterDragon


class BotArgs(TypedDict):
    """TypedDict for bot arguments."""

    bot: Required[WinterDragon]
    db_session: NotRequired[Session]


class CogFlags(IntFlag):
    """Flags for Cog behavior."""

    AutoLoad = auto()
    """Flag to indicate that the cog should be auto-loaded."""
    AutoReload = auto()
    """Flag to indicate that the cog should be auto-reloaded on file changes."""
    _HasAppCommandMentions = auto()


default_flags = CogFlags(CogFlags.AutoLoad | CogFlags.AutoReload)


class Cog(commands.Cog, LoggerMixin):
    """Cog is a subclass of commands.Cog that represents a cog in the WinterDragon bot."""

    bot: WinterDragon
    cache: ClassVar[AppCommandCache] = AppCommandCache()
    flags: CogFlags = default_flags

    # Expose cache methods on the cog for easier access
    get_app_command = cache.get_app_command
    get_command_mention = cache.get_command_mention

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Cog instance.

        Sets up a error handler, app command error handler, and logger for the cog.
        """
        self.bot = kwargs["bot"]
        self.session = kwargs.get("db_session", Session(engine))
        self._auto_reloader = AutoReloadWatcher(bot=self.bot, cog_cls=type(self))

        if not self.has_error_handler():
            # Mention class name from the inheriting subclass.
            self.logger.warning(t"{self.__class__} has no error handler!")
        if not self.has_app_command_error_handler():
            # Mention class name from the inheriting subclass.
            self.logger.warning(t"{self.__class__} has no app command error handler!")

        for listener in self.get_listeners():
            self.logger.debug(listener)

        # Don't start the auto_load loop for the abstract/base Cog classes
        # (we only want concrete subclasses to be able to auto-load themselves).
        if self.__class__ not in (Cog, GroupCog):
            self.bot.loop.create_task(self.auto_load())
            self._auto_reloader.register()

    def __init_subclass__(cls: type[Self], *, auto_load: bool = True, flags: CogFlags | None = None) -> None:
        """Configure loader and hot-reload behavior for subclasses."""
        super().__init_subclass__()
        if flags:
            cls.flags = flags
        if auto_load:
            cls.flags |= CogFlags.AutoLoad
        else:
            cls.flags &= ~CogFlags.AutoLoad

    @property
    def has_app_command_mentions(self) -> bool:
        """Indicates whether the cog has app command mentions."""
        return bool(self.flags & CogFlags._HasAppCommandMentions)  # noqa: SLF001

    async def cog_load(self) -> None:
        """When loaded, start the add_mentions and add_disabled_check loops."""
        self.add_mentions.start()

    async def auto_load(self) -> None:
        """Load the cog if auto_load is True."""
        cls = self.__class__
        if self.__cog_name__ in self.bot.cogs:
            # prevent discord.py from raising an error (simply cleans up logs :) )
            return
        if cls.flags & CogFlags.AutoLoad:
            self.logger.debug(t"Auto loaded Cog {cls.__name__}")
            await self.bot.add_cog(self)

    async def cog_unload(self) -> None:
        """Stop background loops and unregister any auto-reload watcher."""
        if self.add_mentions.is_running():
            self.add_mentions.stop()
        self._auto_reloader.deregister()

    @loop(count=1)
    async def add_mentions(self) -> None:
        """Add app command mentions to the bot if it hasn't been done yet."""
        if not self.has_app_command_mentions:
            self.logger.debug(t"Adding app_commands to cache. {Cog.cache=}")
            await Cog.cache.update_app_commands_cache(self.bot)
            self.flags |= CogFlags._HasAppCommandMentions  # noqa: SLF001

    @add_mentions.before_loop
    async def before_loops(self) -> None:
        """Wait until the bot is ready before adding mentions and disabled checks."""
        await self.bot.wait_until_ready()

    @_cog_special_method
    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        """Handle errors that occur during command invocation."""
        if not isinstance(error, commands.CommandError):
            # Documentation mentions that `error` is CommandError, however it's type hinted with Exception?
            # Just check it here just in case.
            self.logger.error(t"Non-CommandError passed to cog_command_error: {error}", exc_info=error)
            return
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


class GroupCog(Cog):
    """GroupCog is a subclass of Cog that represents a cog with app commands group functionality."""

    # Reflect difference in commands.GroupCog
    __cog_is_app_commands_group__ = True
