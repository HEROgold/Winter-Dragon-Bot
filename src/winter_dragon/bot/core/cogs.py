"""Module that contains Cogs, which are extended classes of discord.ext.commands.Cog/GroupCog."""
from itertools import chain
from typing import Any, NotRequired, Required, Self, TypedDict, Unpack

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands._types import BotT
from discord.ext.commands.context import Context
from sqlmodel import Session, select

from winter_dragon.bot.core.app_command_cache import AppCommandCache
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.errors.factory import ErrorFactory
from winter_dragon.database import engine
from winter_dragon.database.tables.command import Commands
from winter_dragon.database.tables.disabled_commands import DisabledCommands
from winter_dragon.logging import LoggerMixin


class BotArgs(TypedDict):
    """TypedDict for bot arguments."""

    bot: Required[WinterDragon]
    db_session: NotRequired[Session]

class Cog(commands.Cog, LoggerMixin):
    """Cog is a subclass of commands.Cog that represents a cog in the WinterDragon bot.

    Args:
    ----
        bot (WinterDragon): The instance of the WinterDragon bot.
        logger (logging.Logger): The logger for the cog.

    """

    bot: WinterDragon

    def __init_subclass__(cls: type[Self], *, auto_load: bool = False, **kwargs: Any) -> None:  # noqa: ANN401
        """Automatically load the cog if auto_load is True."""
        super().__init_subclass__(**kwargs)
        cls.__cog_auto_load__ = auto_load

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Cog instance.

        Sets up a error handler, app command error handler, and logger for the cog.
        """
        self.bot = kwargs.get("bot")
        self.session = kwargs.get("db_session", Session(engine))
        self.cache = AppCommandCache(self.bot)

        # Expose cache methods on the cog for easier access
        self.get_app_command = self.cache.get_app_command
        self.get_command_mention = self.cache.get_command_mention

        if not self.has_error_handler():
            # Mention class name from the inheriting subclass.
            self.logger.warning(f"{self.__class__} has no error handler!")
        if not self.has_app_command_error_handler():
            # Mention class name from the inheriting subclass.
            self.logger.warning(f"{self.__class__} has no app command error handler!")

        for listener in self.get_listeners():
            self.logger.debug(listener)


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
        statement = select(DisabledCommands).join(Commands).where(
            (Commands.qual_name == qual_name) &
            (
                (DisabledCommands.target_id == user_id) |
                (DisabledCommands.target_id == channel_id) |
                (DisabledCommands.target_id == guild_id)
            ),
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

    @loop(count=1)
    async def auto_load(self) -> None:
        """Automatically load the cog if __cog_auto_load__ is True."""
        if self.__cog_auto_load__:
            self.logger.info(f"Auto-loading {self.__class__.__name__}")
            await self.bot.add_cog(self)

    @loop(count=1)
    async def add_mentions(self) -> None:
        """Add app command mentions to the bot if it hasn't been done yet."""
        if not self.bot.has_app_command_mentions:
            self.logger.debug(f"Adding app_commands cache to {self.bot}")
            await self.bot.update_app_commands_cache()
            self.bot.has_app_command_mentions = True

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
    async def cog_command_error(self, ctx: Context[BotT], error: commands.CommandError) -> None: # pyright: ignore[reportIncompatibleMethodOverride]
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
