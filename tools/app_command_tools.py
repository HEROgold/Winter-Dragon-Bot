
import logging

import discord # type: ignore
from discord import app_commands
from discord.ext import commands, tasks

import config


class ACT():
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.tree = self.bot.tree
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.fetch_app_commands.start()

    @tasks.loop(reconnect=False)
    async def fetch_app_commands(self) -> None:
        self.app_commands = await self.tree.fetch_commands()

    @fetch_app_commands.after_loop
    async def fetch_app_commands_after(self) -> None:
        self.fetch_app_commands.stop()

    def is_group(self, command:app_commands.AppCommand) -> None:
        try:
            for _ in command:
                return True
        except TypeError:
            return False

    def get_app_command(self, command:app_commands.AppCommand|app_commands.Command, guild:discord.Guild=None) -> app_commands.AppCommand:
        if not self.app_commands:
            raise AttributeError(f"app_commands is not found in {self.__class__}")
        self.logger.debug(f"Getting {command.name} from {self.app_commands}")
        for app_command in self.app_commands:
            self.logger.debug(f"Checking for match: {command.name}, {app_command.name}")
            if self.is_group(app_command):
                self.logger.debug(f"{app_command.name} is iterable")
            if command.name == app_command.name:
                self.logger.debug(f"Found {app_command}")
                break 
        else:
            self.logger.debug(f"{command.name} not found in {self.app_commands}")
        self.logger.debug(f"Returning {app_command}")
        return app_command
