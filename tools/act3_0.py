import asyncio
import logging
from typing import Any, Optional, Self

import discord
from discord import app_commands
from tools.caching import memoize

from tools.config_reader import config
from _types.bot import WinterDragon

Commands = app_commands.AppCommand | app_commands.Command


# Suggested ai code to find full qual name from a appcommand Command
def get_full_name(command: app_commands.Command) -> str:
    names = []

    current_command = command
    while current_command.parent:
        names.append(current_command.name)
        current_command = current_command.parent

    names.append(current_command.name)
    return " ".join(reversed(names))


class CommandNotFound(Exception):
    pass


class Converter:
    bot: WinterDragon
    tree: app_commands.CommandTree
    logger: logging.Logger
    fetched_commands: list[app_commands.AppCommand]

    _instance: Optional[Self] = None


    def __new__(cls, bot: WinterDragon) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, bot: WinterDragon) -> None:
        self.bot = bot
        self.tree = self.bot.tree
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

        # Schedule the fetch_commands method to run in the existing event loop
        asyncio.ensure_future(self.fetch_commands())


    async def fetch_commands(self) -> None:
        self.fetched_commands = self.fetched_commands or await self.tree.fetch_commands()


    @staticmethod
    def is_group(check: Any) -> bool:
        return isinstance(check, app_commands.Group)


    @staticmethod
    def is_subcommand(check: Any) -> bool:
        return isinstance(check, app_commands.AppCommandGroup)


    def get_app_sub_command(self, command: Commands) -> Optional[app_commands.AppCommand]:
        if not self.is_group(command.parent):
            raise CommandNotFound("Got AppCommand when expecting a SubCommand")
        return (command, command.mention) if self.is_subcommand(command) else None


    async def get_app_command(self, command: Commands) -> Optional[app_commands.AppCommand]:
        if isinstance(command, app_commands.AppCommand):
            self.logger.debug(f"Quick return for {command.name}, already an AppCommand")
            return command

        if self.is_subcommand(command):
            raise CommandNotFound("Got a SubCommand when expecting an AppCommand")

        return next(
            (
                fetched_command
                for fetched_command in self.fetched_commands
                if fetched_command.name == command.name
            ),
            None,
        )

## from ACT v1 and AI

class CommandNotFound(Exception):
    pass

class Converter:
    bot: WinterDragon
    tree: app_commands.CommandTree
    logger: logging.Logger

    _instance: Optional[Self] = None


    def __new__(cls, bot: WinterDragon) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, bot: WinterDragon) -> Self:
        self.bot = bot
        self.tree = self.bot.tree
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @staticmethod
    def is_group(app_command: Any) -> bool:
        return isinstance(app_command, (app_commands.AppCommandGroup, app_commands.Group))


    @staticmethod
    def is_subcommand(app_command: app_commands.AppCommand, command: app_commands.Command) -> bool:
        return any(
            isinstance(option, app_commands.AppCommandGroup)
            and command.name in option.name
            for option in app_command.options
        )


    @memoize
    async def get_app_sub_command(
        self,
        sub_command: app_commands.Command,
        guild: discord.Guild = None,
        app_command: app_commands.AppCommand = None
    ) -> Optional[tuple[app_commands.AppCommand, str]]:
        if not sub_command:
            raise CommandNotFound

        if not app_command or app_command is None:
            app_command = await self.get_app_command(sub_command.parent, guild)

        if self.is_group(app_command) and self.is_subcommand(app_command, sub_command):
            custom_mention = f"</{app_command.name} {sub_command.name}:{app_command.id}>"
            return app_command, custom_mention

        return None


    @memoize
    async def get_app_command(
        self,
        command: app_commands.AppCommand | app_commands.Command,
        guild: discord.Guild = None
    ) -> Optional[app_commands.AppCommand]:
        if isinstance(command, app_commands.AppCommand):
            return command

        if not command:
            raise CommandNotFound

        app_commands_list = await self.tree.fetch_commands(guild=guild)

        return next(
            (
                app_command
                for app_command in app_commands_list
                if command.name == app_command.name
            ),
            None,
        )


# Combined two examples above

# import asyncio
# import logging
# from typing import Any, Optional, Self

# import discord
# from discord import app_commands
# from discord.ext import commands

# from tools.config_reader import config
# from tools.caching import memoize
# from _types.bot import WinterDragon

# class CommandNotFound(Exception):
#     pass

# class Converter:
#     bot: WinterDragon
#     tree: app_commands.CommandTree
#     logger: logging.Logger
#     parameter_args: Optional[Any] = None

#     _instance: Optional[Self] = None

#     def __new__(cls, bot: WinterDragon) -> Self:
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#         return cls._instance

#     def __init__(self, bot: WinterDragon) -> Self:
#         self.bot = bot
#         self.tree = self.bot.tree
#         self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

#     def is_group(self, app_command: Any) -> bool:
#         return isinstance(app_command, (app_commands.AppCommandGroup, app_commands.Group))

#     def is_subcommand(self, app_command: app_commands.AppCommand, command: app_commands.Command) -> bool:
#         return any(
#             isinstance(option, app_commands.AppCommandGroup)
#             and command.name in option.name
#             for option in app_command.options
#         )

#     @memoize
#     async def get_app_sub_command(
#         self,
#         sub_command: app_commands.Command,
#         guild: discord.Guild = None,
#         app_command: app_commands.AppCommand = None
#     ) -> Optional[tuple[app_commands.AppCommand, str]]:
#         if not sub_command:
#             raise CommandNotFound

#         if not app_command or app_command is None:
#             app_command = await self.get_app_command(sub_command.parent, guild)

#         if self.is_group(app_command) and self.is_subcommand(app_command, sub_command):
#             custom_mention = f"</{app_command.name} {sub_command.name}:{app_command.id}>"
#             return app_command, custom_mention

#         return None

#     @memoize
#     async def get_app_command(
#         self,
#         command: app_commands.AppCommand | app_commands.Command,
#         guild: discord.Guild = None
#     ) -> Optional[app_commands.AppCommand]:
#         if isinstance(command, app_commands.AppCommand):
#             return command

#         if not command:
#             raise CommandNotFound

#         app_commands_list = await self.tree.fetch_commands(guild=guild)

#         return next(
#             (
#                 app_command
#                 for app_command in app_commands_list
#                 if command.name == app_command.name
#             ),
#             None,
#         )

#     async def fetch_commands(self) -> None:
#         self.fetched_commands = self.fetched_commands or await self.tree.fetch_commands()

#     def is_group(self, app_command: Any) -> bool:
#         return isinstance(app_command, (app_commands.AppCommandGroup, app_commands.Group))

#     def is_subcommand(self, app_command: app_commands.AppCommand, command: app_commands.Command) -> bool:
#         return any(
#             isinstance(option, app_commands.AppCommandGroup)
#             and command.name in option.name
#             for option in app_command.options
#         )

#     @memoize
#     async def get_app_sub_command(
#         self,
#         sub_command: app_commands.Command,
#         guild: discord.Guild = None,
#         app_command: app_commands.AppCommand = None
#     ) -> Optional[tuple[app_commands.AppCommand, str]]:
#         if not sub_command:
#             raise CommandNotFound

#         if not app_command or app_command is None:
#             app_command = await self.get_app_command(sub_command.parent, guild)

#         if self.is_group(app_command) and self.is_subcommand(app_command, sub_command):
#             custom_mention = f"</{app_command.name} {sub_command.name}:{app_command.id}>"
#             return app_command, custom_mention

#         return None

#     @memoize
#     async def get_app_command(
#         self,
#         command: app_commands.AppCommand | app_commands.Command,
#         guild: discord.Guild = None
#     ) -> Optional[app_commands.AppCommand]:
#         if isinstance(command, app_commands.AppCommand):
#             return command

#         if not command:
#             raise CommandNotFound

#         app_commands_list = await self.tree.fetch_commands(guild=guild)

#         return next(
#             (
#                 app_command
#                 for app_command in app_commands_list
#                 if command.name == app_command.name
#             ),
#             None,
#         )

#     async def with_parameters(
#         self,
#         command: commands.Command,
#         **kwargs
#     ) -> str:
#         raise NotImplementedError("Not yet supported on Discord's end")

#     @staticmethod
#     def get_full_name(command: app_commands.Command) -> str:
#         names = []

#         current_command = command
#         while current_command.parent:
#             names.append(current_command.name)
#             current_command = current_command.parent

#         names.append(current_command.name)
#         return " ".join(reversed(names))
