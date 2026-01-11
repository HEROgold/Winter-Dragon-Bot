"""Module that contains Cogs, which are extended classes of discord.ext.commands.Cog/GroupCog."""

from __future__ import annotations

from enum import IntFlag, auto
from itertools import chain
from typing import TYPE_CHECKING, ClassVar, NotRequired, Required, Self, TypedDict, Unpack

import discord
from discord import app_commands
from discord.ext import commands
from herogold.log import LoggerMixin
from sqlmodel import Session, select

from winter_dragon.bot.core.app_command_cache import AppCommandCache
from winter_dragon.bot.core.auto_reload import AutoReloadWatcher
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


class CogFlags(IntFlag):
    """Flags for Cog behavior."""

    AutoLoad = auto()
    """Flag to indicate that the cog should be auto-loaded."""
    AutoReload = auto()
    """Flag to indicate that the cog should be auto-reloaded on file changes."""
    HasAppCommandMentions = auto()
    """Flag to indicate that the cog has app command mentions."""


default_flags = CogFlags(CogFlags.AutoLoad | CogFlags.AutoReload)


class Cog(commands.Cog, LoggerMixin):
    """Cog is a subclass of commands.Cog that represents a cog in the WinterDragon bot."""

    bot: WinterDragon
    cache: ClassVar[AppCommandCache] = AppCommandCache()
    flags: CogFlags

    # Expose cache methods on the cog for easier access
    get_app_command = cache.get_app_command
    get_command_mention = cache.get_command_mention

    @property
    def has_app_command_mentions(self) -> bool:
        """Indicates whether the cog has app command mentions."""
        return bool(self.flags & CogFlags.HasAppCommandMentions)

    def __init_subclass__(cls: type[Self], *, auto_load: bool = True, flags: CogFlags = default_flags) -> None:
        """Configure loader and hot-reload behavior for subclasses."""
        super().__init_subclass__()
        cls.flags = flags
        cls.flags |= CogFlags.AutoLoad if auto_load else ~CogFlags.AutoLoad

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Cog instance.

        Sets up a error handler, app command error handler, and logger for the cog.
        """
        self.bot = kwargs["bot"]
        self.session = kwargs.get("db_session", Session(engine))
        self._auto_reloader = AutoReloadWatcher(
            bot=self.bot,
            cog_cls=self.__class__,
        )

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
        if self.__class__ not in (Cog, GroupCog):
            self.bot.loop.create_task(self.auto_load())
            self._auto_reloader.register()

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
        """Load the cog if auto_load is True."""
        cls = self.__class__
        self.logger.info(f"Auto-loading Cog {cls.__name__}: {bool(cls.flags & CogFlags.AutoLoad)}")
        if self.__cog_name__ in self.bot.cogs:
            # prevent discord.py from raising an error (simply cleans up logs :) )
            return
        if cls.flags & CogFlags.AutoLoad:
            await self.bot.add_cog(self)

    def cog_unload(self) -> None:  # type: ignore[override]
        """Stop background loops and unregister any auto-reload watcher."""
        if self.add_mentions.is_running():
            self.add_mentions.stop()
        if self.add_disabled_check.is_running():
            self.add_disabled_check.stop()
        self._auto_reloader.deregister()

    @loop(count=1)
    async def add_mentions(self) -> None:
        """Add app command mentions to the bot if it hasn't been done yet."""
        if not self.has_app_command_mentions:
            self.logger.debug(f"Adding app_commands to cache. {Cog.cache=}")
            await Cog.cache.update_app_commands_cache(self.bot)
            self.flags |= CogFlags.HasAppCommandMentions

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


class GroupCog(Cog):
    """GroupCog is a subclass of Cog that represents a cog with app commands group functionality."""

    # Reflect difference in commands.GroupCog
    __cog_is_app_commands_group__ = True
