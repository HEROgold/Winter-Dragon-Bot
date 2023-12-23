import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands # , tasks
from discord.ext.commands._types import BotT
from discord.ext.commands.context import Context

from _types.bot import WinterDragon
from tools.config_reader import config
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


    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.ErrorHandler = ErrorHandler
        self.bot = get_arg(args, WinterDragon) or kwargs.get("bot")
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

        if not self.has_error_handler():
            self.logger.warning(f"{self.__class__} has no error handler!")
        if not self.has_app_command_error_handler():
            self.logger.warning(f"{self.__class__} has no app command error handler!")
        
        for listener in self.get_listeners():
            self.logger.debug(f"{listener=}")


    async def cog_command_error(self, ctx: Context[BotT], error: Exception) -> None:
        self.ErrorHandler(self.bot, ctx, error)


    async def cog_load(self) -> None:
        self.add_mentions.start()

    @tasks.loop(count=1)
    async def add_mentions(self):
        # await self.add_command_mentions()
        if not self.bot.has_app_command_mentions:
            await self.bot.update_app_commands_cache()
            self.bot.has_app_command_mentions = True

    @add_mentions.before_loop
    async def before_add_mentions(self):
        await self.bot.wait_until_ready()


    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        self.ErrorHandler(self.bot, interaction, error)


    def get_command_mention(self, command: app_commands.Command):
        if not isinstance(command, app_commands.Command): # type:ignore
            raise TypeError(f"Expected app_commands.commands.Command but got {type(command)} instead")

        if cmd := self.bot.get_app_command(command.qualified_name):
            return cmd.mention


class GroupCog(Cog):
    """
    GroupCog is a subclass of Cog that represents a cog with app commands group functionality.
    """

    # Reflect difference in commands.GroupCog
    __cog_is_app_commands_group__ = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)