import logging
from typing import Self

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

from tools.config_reader import config
from tools.caching import memoize
from _types.bot import WinterDragon


class CommandNotFound(Exception):
    pass


class Converter:
    bot: WinterDragon
    tree: app_commands.CommandTree
    logger: logging.Logger
    parameter_args = None # Not implemented
    _instance = None

    def __new__(cls, bot: WinterDragon) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, bot: WinterDragon) -> Self:
        self.bot = bot
        self.tree = self.bot.tree
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

    def is_group(self, app_command: app_commands.AppCommand) -> bool:
        self.logger.debug(f"Checking is_group: {app_command}")
        return any(
            type(i) in [
                app_commands.AppCommandGroup,
                app_commands.Group,
                app_commands.commands.Group
            ]
            for i in app_command.options
        )

    def is_subcommand(
        self,
        app_command:app_commands.AppCommand,
        command:app_commands.Command
    ) -> bool:
        for option in app_command.options:
            if (
                type(option) == app_commands.AppCommandGroup
                and command.name in option.name
            ):
                self.logger.debug(f"Found subcommand: {command.name}")
                return True
        return False


    @memoize
    async def get_app_sub_command(
        self,
        sub_command: app_commands.Command,
        guild: discord.Guild = None,
        app_command: app_commands.AppCommand = None
    ) -> tuple[app_commands.AppCommand, str] | None:
        """
        Retrieves the sub-command of an app.
    
        Args:
            self: The instance of the class.
            sub_command (app_commands.Command): The sub-command to retrieve.
            guild (discord.Guild, optional): The guild to retrieve the sub-command from. Defaults to None.
            app_command (app_commands.AppCommand, optional): The app command to retrieve the sub-command from. Defaults to None.
    
        Returns:
            tuple[app_commands.AppCommand, str] | None: A tuple containing the app command and a custom mention string, or None if the sub-command is not found.
    
        Raises:
            CommandNotFound: Raised when the sub-command is not found.
        """
        if not sub_command:
            raise CommandNotFound

        self.logger.debug(f"Trying to get sub AppCommand: {sub_command.name}, {guild}, {app_command}")

        if not app_command or app_command is None:
            app_command = await self.get_app_command(sub_command.parent, guild)

        if self.is_group(app_command):
            self.logger.debug(f"{app_command.name} is a group")
            if self.is_subcommand(app_command, sub_command):
                custom_mention = f"</{app_command.name} {sub_command.name}:{app_command.id}>"
        else:
            self.logger.debug(f"Subcommand {sub_command.name} not found")
            return None

        self.logger.debug(f"Returning {app_command=} {sub_command=}")
        return app_command, custom_mention


    @memoize
    async def get_app_command(
        self,
        command: app_commands.AppCommand | app_commands.Command,
        guild: discord.Guild = None
    ) -> app_commands.AppCommand:
        """Gets the AppCommand from a Command"""
        if type(command) == app_commands.AppCommand:
            self.logger.debug(f"Quick return for {command.name}, already an AppCommand")
            return command

        if not command:
            raise CommandNotFound

        if self.is_group(command):
            self.logger.debug("command is group! when not expected")

        self.logger.debug(f"Trying to get AppCommand: {command.name}")
        # app_commands_list = await self._get_commands(guild)
        app_commands_list = await self.tree.fetch_commands(guild=guild)
        self.logger.debug(f"cmd list: {[i.name for i in app_commands_list]}")

        for app_command in app_commands_list:
            # self.logger.debug(f"Checking for match: {command.name}, {app_command.name}")
            if command.name == app_command.name:
                self.logger.debug(f"Found {app_command}")
                break
        else:
            if guild:
                self.logger.warning(f"Command {command.name} not found, trying global commands.") # {app_commands_list}
                return await self.get_app_command(command, guild=None)
            else:
                self.logger.debug(f"Command {command.name} not found")
            return None
        self.logger.debug(f"Returning {app_command}")
        return app_command


    # TODO, return pre-filled arguments for a given command
    # Needs to work both with and without sub commands.
    # Chat bar: /steam show percent:100, Clickable: </steam show:1064592221204140132>
    # Doesn't work with discord's api (yet?)!!
    async def with_parameters(
        self,
        command: commands.Command,
        **kwargs
    ) -> str:
        raise NotImplementedError("Not yet supported on discord's end")
        # app_command, custom_mention = await self.get_app_sub_command(command)
        # args = " ".join(f"{k}:{v}" for k, v in kwargs.items())
        # _test = f"{custom_mention[:-1]} {args}>"
        # try:
        #     self.logger.debug(command.clean_params)
        # except AttributeError:
        #     pass
        # self.logger.debug(app_command.to_dict())
        # return _test
