from asyncio import iscoroutinefunction
import logging
from typing import Any, Self

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config


def memoize(func):
    """
    (c) 2021 Nathan Henrie, MIT License
    https://n8henrie.com/2021/11/decorator-to-memoize-sync-or-async-functions-in-python/
    """
    logger = logging.getLogger(f"{config.Main.BOT_NAME}.memoize")
    cache = {}

    async def memoized_async_func(*args, **kwargs) -> Any:
        key = (args, frozenset(sorted(kwargs.items())))
        if key in cache:
            logger.debug(f"returning cached async function {cache[key]=}")
            return cache[key]
        result = await func(*args, **kwargs)
        cache[key] = result
        logger.debug(f"caching async function {cache[key]=}")
        return result

    def memoized_sync_func(*args, **kwargs) -> Any:
        key = (args, frozenset(sorted(kwargs.items())))
        if key in cache:
            logger.debug(f"returning cached function {cache[key]=}")
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        logger.debug(f"caching function {cache[key]=}")
        return result

    return memoized_async_func if iscoroutinefunction(func) else memoized_sync_func


class CommandNotFound(Exception):
    pass


class Converter:
    bot: commands.Bot
    tree: app_commands.CommandTree
    logger: logging.Logger
    parameter_args = None # Not implemented


    def __init__(self, bot: commands.Bot) -> Self:
        self.bot = bot
        self.tree = self.bot.tree
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    def is_group(self, app_command: app_commands.AppCommand) -> bool:
        self.logger.debug(f"Checking is_group: {app_command.name}")
        return any(type(i) == app_commands.AppCommandGroup for i in app_command.options)

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
        """Returns a AppCommand and a string that can be used to mention the subcommand"""
        if not sub_command:
            raise CommandNotFound
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
        self.logger.debug(f"Trying to get AppCommand: {command.name}")
        # app_commands_list = await self._get_commands(guild)
        app_commands_list = await self.tree.fetch_commands(guild=guild)
        self.logger.debug(f"cmd list: {app_commands_list}")
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


    # TODO, return pre-filled arguments for a given command
    # Doesn't work with discord's api (yet?)
    # Needs to work both with and without sub commands.
    # Chat bar: /steam show percent:100, Clickable: </steam show:1064592221204140132>
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

