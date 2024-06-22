import logging
from itertools import chain

import discord
from discord import User, app_commands
from discord.ext import commands  # , tasks
from discord.ext.commands._types import BotT
from discord.ext.commands.context import Context

from _types.bot import WinterDragon
from config import config
from tools.database_tables import (
    Channel,
    DisabledCommands,
    GuildCommands,
    Session,
    engine,
)
from tools.database_tables import Command as DbCommand
from tools.database_tables import User as DbUser
from tools.error_handler import ErrorHandler
from tools.utils import get_arg

from .tasks import tasks


class Cog(commands.Cog):
    """
    Cog is a subclass of commands.Cog that represents a cog in the WinterDragon bot.

    Args:
        bot (WinterDragon): The instance of the WinterDragon bot.
        logger (logging.Logger): The logger for the cog.
    """

    bot: WinterDragon
    logger: logging.Logger


    def __init__(self, *args, **kwargs) -> None:
        self.ErrorHandler = ErrorHandler
        self.bot = get_arg(args, WinterDragon) or kwargs.get("bot") # type: ignore
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

        if self.bot:
            self.bot.default_intents = self.bot.intents
        if not self.has_error_handler():
            self.logger.warning(f"{self.__class__} has no error handler!")
        if not self.has_app_command_error_handler():
            self.logger.warning(f"{self.__class__} has no app command error handler!")

        for listener in self.get_listeners():
            self.logger.debug(f"{listener=}")


    def is_command_disabled(self, interaction: discord.Interaction) -> bool:
        # Get db info and check if command is disabled on guild, channel, or just for this user.
        # TODO: Needs testing
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.message.author if isinstance(interaction, commands.Context) else interaction.user

        with Session(engine) as session:
            targets: list[GuildCommands | Channel | User | None] = []
            if guild:
                targets.append(session.query(GuildCommands).where(GuildCommands.guild_id == guild.id).first())
            if channel:
                targets.append(session.query(Channel).where(Channel.id == channel.id).first())
            if user:
                targets.append(session.query(DbUser).where(DbUser.id == user.id).first()) # type: ignore

            disabled_ids = [
                c.command_id
                for c in session.query(DisabledCommands).join(
                DbCommand, DisabledCommands.command_id == DbCommand.id,
                ).where(
                    DbCommand.qual_name == interaction.command.qualified_name,
                ).all()
            ]

        return next(
            (
                True
                for target in targets
                if target is not None and target.id in disabled_ids
            ),
            False,
        )


    def is_command_enabled(self, interaction: discord.Interaction) -> bool:
        return not self.is_command_disabled(interaction)


    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        self.ErrorHandler(self.bot, ctx, error)


    async def cog_load(self) -> None:
        self.add_mentions.start()
        self.add_disabled_check.start()


    @tasks.loop(count=1)
    async def add_mentions(self) -> None:
        # await self.add_command_mentions()
        if not self.bot.has_app_command_mentions:
            self.logger.debug(f"Adding app_commands cache to {self.__cog_name__}")
            await self.bot.update_app_commands_cache()
            self.bot.has_app_command_mentions = True


    @tasks.loop(count=1)
    async def add_disabled_check(self) -> None:
        for command in chain(self.walk_commands(), self.walk_app_commands()):
            if isinstance(command, app_commands.Group):
                continue
            self.logger.debug(f"Adding is command disabled check to {command.qualified_name}")
            command.add_check(self.is_command_enabled) # type: ignore

    @add_mentions.before_loop
    @add_disabled_check.before_loop
    async def before_loops(self) -> None:
        await self.bot.wait_until_ready()


    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        self.ErrorHandler(self.bot, interaction, error)


    def get_command_mention(self, command: app_commands.Command) -> str | None:
        """
        Return a command string from a given functiontype. (Decorated with app_commands.command)

        Parameters
        -----------
        :param:`command`: :class:`app_commands.Command`
            The command to convert.

        Returns
        -------
        :class:`str | None`
            The string used to use the command in discord.

        Raises
        ------
        :class:`TypeError`
            If the command is not an instance of app_commands.Command.
        """
        if not isinstance(command, app_commands.Command): # type:ignore
            msg = f"Expected app_commands.commands.Command but got {type(command)} instead"
            raise TypeError(msg)

        if cmd := self.bot.get_app_command(command.qualified_name):
            return cmd.mention
        self.logger.warning(f"Can't find {command}")
        return None


class GroupCog(Cog):
    """
    GroupCog is a subclass of Cog that represents a cog with app commands group functionality.
    """

    # Reflect difference in commands.GroupCog
    __cog_is_app_commands_group__ = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
