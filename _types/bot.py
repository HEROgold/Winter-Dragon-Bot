import datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext.commands import AutoShardedBot, CommandError
from discord.ext.commands._types import BotT
from discord.ext.commands.context import Context
from discord.ext.commands.help import HelpCommand


# TODO: add explicit connector see:
# FIXME: https://discord.com/channels/336642139381301249/1150903023091060746/1150919294864072784
class WinterDragon(AutoShardedBot):
    """
    WinterDragon is a subclass of AutoShardedBot that represents a bot with additional attributes and methods specific to the Winter Dragon bot.

    Args:
        command_prefix (str): The prefix used to invoke commands.
        help_command (HelpCommand | None, optional): The custom help command to use. Defaults to None.
        tree_cls (type[app_commands.CommandTree[Any]], optional): The custom command tree class to use. Defaults to app_commands.CommandTree.
        description (str | None, optional): The description of the bot. Defaults to None.
        intents (discord.Intents): The intents to enable for the bot.
        **options (Any): Additional options to pass to the superclass constructor.
    """

    launch_time: datetime.datetime

    def __init__(
        self,
        command_prefix,
        *,
        help_command: HelpCommand | None = None,
        tree_cls: type[app_commands.CommandTree[Any]] = app_commands.CommandTree,
        description: str | None = None,
        intents: discord.Intents,
        **options: Any
    ) -> None:
        super().__init__(command_prefix, help_command=help_command, tree_cls=tree_cls, description=description, intents=intents, **options)


    # TODO: on_error, and on_command_error might need to log errors to own log
    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        return super().on_error(event_method, *args, **kwargs)
    
    async def on_command_error(self, context: Context[BotT], exception: CommandError) -> None:
        return super().on_command_error(context, exception)

