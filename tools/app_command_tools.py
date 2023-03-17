import logging
from typing import Self

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config


class CommandNotFound(Exception):
    pass

class Converter:
    bot: commands.Bot
    tree: app_commands.CommandTree
    logger: logging.Logger
    cache: dict = None

    def __init__(self, bot: commands.Bot) -> Self:
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
        """Returns the full app_command and a string that can be used to mention the subcommand"""
        if not sub_command:
            raise CommandNotFound
        if not app_command:
            app_command = await self.get_app_command(sub_command.parent, guild)
        if self.is_group(app_command):
            self.logger.debug(f"{app_command.name} is a group")
            if self.is_subcommand(app_command, sub_command):
                custom_mention = f"</{app_command.name} {sub_command.name}:{app_command.id}>"
        else:
            self.logger.debug(f"Subcommand {sub_command.name} not found")
            return None
        self.logger.debug(f"Returning {app_command} {sub_command}")
        return app_command, custom_mention

    async def get_app_command(self, command:app_commands.AppCommand|app_commands.Command, guild:discord.Guild=None) -> app_commands.AppCommand:
        """Gets the app_command from a command"""
        if type(command) == app_commands.AppCommand:
            self.logger.debug(f"Quick return for {command.name}, already an AppCommand")
            return command
        if not command:
            raise CommandNotFound
        self.logger.debug(f"Trying to get AppCommand: {command.name}")
        app_commands_list = await self._get_commands(guild)
        for app_command in app_commands_list:
            # self.logger.debug(f"Checking for match: {command.name}, {app_command.name}")
            if command.name == app_command.name:
                self.logger.debug(f"Found {app_command}")
                break
        else:
            if guild:
                self.logger.debug(f"Command {command.name} not found in {app_commands_list}, trying global commands.")
                await self.get_app_command(command, guild=None)
            else:
                self.logger.debug(f"Command {command.name} not found")
            return None
        self.logger.debug(f"Returning {app_command}")
        return app_command

    async def _cache_handler(self, guild: discord.Guild) -> None:
        if not self.cache:
            self.logger.debug("Creating cache")
            self.cache = {}
        if not guild:
            self.logger.debug("getting global commands list")
            try:
                self.cache["global"]
            except KeyError:
                self.cache = {"global": await self.tree.fetch_commands()}
        else:
            self.logger.debug(f"getting {guild} commands list")
            try:
                self.cache[str(guild.id)]
            except KeyError:
                self.cache = {str(guild.id): await self.tree.fetch_commands(guild=guild)}

    async def _get_commands(self, guild: discord.Guild) -> list[app_commands.AppCommand]:
        await self._cache_handler(guild)
        return self.cache[str(guild.id)] if guild else self.cache["global"]
