import logging

import discord # type: ignore
from discord import app_commands
from discord.ext import commands

import config

class CommandNotFound(Exception):
    pass

class Converter():
    bot: commands.Bot
    tree: app_commands.CommandTree
    logger: logging.Logger

    def __init__(self, bot) -> None:
        self.bot = bot
        self.tree = self.bot.tree
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    def is_group(self, app_command:app_commands.AppCommand) -> None:
        self.logger.debug(f"Checking is_group: {app_command.name}")
        return any(type(i) == app_commands.AppCommandGroup for i in app_command.options)

    def is_subcommand(self, app_command:app_commands.AppCommand, command:app_commands.Command) -> None:
        for option in app_command.options:
            if (
                type(option) == app_commands.AppCommandGroup
                and command.name in option.name
            ):
                self.logger.debug(f"Found subcommand: {command.name}")
                return True
        return False

    async def get_app_sub_command(self, sub_command:app_commands.Command, guild:discord.Guild=None, app_command:app_commands.AppCommand=None) -> tuple[app_commands.AppCommand, str]:
        """Returns the full app_command and a custom mention that can be used to mention the subcommand"""
        if not app_command:
            app_command = await self.get_app_command(sub_command.parent, guild)
        if self.is_group(app_command):
            self.logger.debug(f"{app_command.name} is a group")
            if self.is_subcommand(app_command, sub_command):
                custom_mention = f"</{app_command.name} {sub_command.name}:{app_command.id}>"
        else:
            self.logger.debug(f"Subcommand {sub_command.name} not found in {self.app_commands}")
            return None
        self.logger.debug(f"Returning {app_command}")
        return app_command, custom_mention

    async def get_app_command(self, command:app_commands.AppCommand|app_commands.Command, guild:discord.Guild=None) -> app_commands.AppCommand:
        """Gets the app_command from a command"""
        if type(command) == app_commands.AppCommand:
            self.logger.debug(f"Quick return for {command.name}, already an AppCommand")
            return command
        self.logger.debug(f"Trying to get AppCommand: {command.name}")
        self.app_commands = await self.tree.fetch_commands(guild=guild)
        for app_command in self.app_commands:
            # self.logger.debug(f"Checking for match: {command.name}, {app_command.name}")
            if command.name == app_command.name:
                self.logger.debug(f"Found {app_command}")
                break
        else:
            self.logger.debug(f"Command {command.name} not found in {self.app_commands}")
            return None
        # self.logger.debug(f"Getting {command.name} from {self.app_commands}")
        self.logger.debug(f"Returning {app_command}")
        return app_command
