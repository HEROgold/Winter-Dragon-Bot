import datetime
import logging
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext.commands import AutoShardedBot, CommandError
from discord.ext.commands._types import BotT
from discord.ext.commands.context import Context
from discord.ext.commands.help import HelpCommand, DefaultHelpCommand
from discord.abc import Snowflake

from tools.config_reader import config


AppCommandStore = dict[str, app_commands.AppCommand]


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
    logger: logging.Logger
    has_app_command_mentions: bool = False
    _global_app_commands: AppCommandStore = {}
    _guild_app_commands: dict[int, AppCommandStore] = {}


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
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}")


        if help_command is None:
            help_command = DefaultHelpCommand()

        super().__init__(command_prefix, help_command=help_command, tree_cls=tree_cls, description=description, intents=intents, **options)


    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        self.logger.exception(f"error in: {event_method}")
        return await super().on_error(event_method, *args, **kwargs)

    async def on_command_error(self, context: Context[BotT], exception: CommandError) -> None:
        self.logger.exception(f"error in command: {context}", exc_info=exception)
        return await super().on_command_error(context, exception)


    # Credits to https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131#file-bot_subclass
    def get_app_command(
        self,
        value: str | int,
        guild: Optional[Snowflake | int] = None,
        fallback_to_global: bool = True,
    ) -> Optional[app_commands.AppCommand]:
        def search_dict(d: AppCommandStore) -> Optional[app_commands.AppCommand]:
            for cmd_name, cmd in d.items():
                if value == cmd_name or (str(value).isdigit() and int(value) == cmd.id):
                    return cmd
            return None

        if guild:
            guild_id = guild if isinstance(guild, int) else guild.id
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not fallback_to_global:
                return search_dict(guild_commands)
            else:
                return search_dict(guild_commands) or search_dict(self._global_app_commands)
        else:
            return search_dict(self._global_app_commands)


    async def update_app_commands_cache(
        self,
        commands: Optional[list[app_commands.AppCommand]] = None,
        guild: Optional[Snowflake | int] = None
    ) -> None:
        def unpack_app_commands(commands: list[app_commands.AppCommand]) -> AppCommandStore:
            ret: AppCommandStore = {}

            def unpack_options(options: list[app_commands.AppCommand | app_commands.AppCommandGroup, app_commands.Argument]):
                for option in options:
                    if isinstance(option, app_commands.AppCommandGroup):
                        ret[option.qualified_name] = option  # type: ignore
                        unpack_options(option.options)  # type: ignore

            for command in commands:
                ret[command.name] = command
                unpack_options(command.options)  # type: ignore

            return ret

        # because we support both int and Snowflake
        # we need to convert it to a Snowflake like object if it's an int
        _guild: Optional[Snowflake] = None
        if guild is not None:
            _guild = discord.Object(guild) if isinstance(guild, int) else guild

        tree: app_commands.CommandTree = self.tree
        # commands.Bot has a built-in tree
        # this should be point to your tree if using discord.Client
        if not commands:
            commands = await tree.fetch_commands(guild=_guild)

        if _guild:
            self._guild_app_commands[_guild.id] = unpack_app_commands(commands)
        else:
            self._global_app_commands = unpack_app_commands(commands)