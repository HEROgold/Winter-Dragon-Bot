"""Module that contains Cogs, which are extended classes of discord.ext.commands.Cog/GroupCog."""
import logging
from itertools import chain
from typing import Unpack

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands._types import BotT
from discord.ext.commands.context import Context
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.error_handler import ErrorHandler
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.bot.core.tasks import loop
from winter_dragon.bot.tools.commands import Commands as CmdTool
from winter_dragon.database import Session, engine
from winter_dragon.database.tables import Channels, DisabledCommands, GuildCommands
from winter_dragon.database.tables import Users as DbUser

from bot.src.winter_dragon.bot._types.kwargs import BotKwarg


class Cog(commands.Cog, LoggerMixin):
    """Cog is a subclass of commands.Cog that represents a cog in the WinterDragon bot.

    Args:
    ----
        bot (WinterDragon): The instance of the WinterDragon bot.
        logger (logging.Logger): The logger for the cog.

    """

    bot: WinterDragon
    logger: logging.Logger

    def __init__(self, **kwargs: Unpack[BotKwarg]) -> None:
        """Initialize the Cog instance.

        Sets up a error handler, app command error handler, and logger for the cog.
        """
        bot = kwargs.get("bot")
        self.bot = bot
        self.session = Session(engine)

        if self.bot:
            self.bot.default_intents = self.bot.intents
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
        # Get db info and check if command is disabled on guild, channel, or just for this user.
        # TODO @HEROgold: Needs testing
        #145
        guild = interaction.guild
        channel = interaction.channel

        if interaction.message is None or not isinstance(interaction, commands.Context):
            user = interaction.user
        else:
            user = interaction.message.author

        targets: list[GuildCommands | Channels | DbUser | None] = []
        if guild:
            targets.append(
                self.session.exec(
                    select(GuildCommands).where(GuildCommands.guild_id == guild.id),
                ).first(),
            )
        if channel:
            targets.append(
                self.session.exec(
                    select(Channels).where(Channels.id == channel.id),
                ).first(),
            )
        if user:
            targets.append(
                self.session.exec(
                    select(DbUser).where(DbUser.id == user.id),
                ).first(),
            )

        # TODO @HEROgold: Rethink the query to get boolean values from the DB directly
        #144
        disabled_commands = list(self.session.exec(select(DisabledCommands)).all())
        disabled_ids = [i.target_id for i in disabled_commands]

        return next(
            (True for target in targets if target and target.id in disabled_ids),
            False,
        )

    def is_command_enabled(self, interaction: discord.Interaction) -> bool:
        """Check if a command is enabled for a guild, channel, or user."""
        return not self.is_command_disabled(interaction)

    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        """Handle errors that occur during command invocation."""
        ErrorHandler(self.bot, ctx, error)

    async def cog_load(self) -> None:
        """When loaded, start the add_mentions and add_disabled_check loops."""
        self.add_mentions.start()
        self.add_disabled_check.start()

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

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Handle the errors that occur during app command invocation."""
        ErrorHandler(self.bot, interaction, error)

    def get_command_mention(self, command: app_commands.Command) -> str:
        """Return a command string from a given functiontype. (Decorated with app_commands.command)."""
        return CmdTool.get_command_mention(self.bot, command)


class GroupCog(Cog):
    """GroupCog is a subclass of Cog that represents a cog with app commands group functionality."""

    # Reflect difference in commands.GroupCog
    __cog_is_app_commands_group__ = True

    def __init__(self, **kwargs: Unpack[BotKwarg]) -> None:
        """Initialize the GroupCog instance with given args and kwargs."""
        super().__init__(**kwargs)
