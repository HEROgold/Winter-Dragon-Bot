import logging
from typing import Any, Self

from discord import app_commands

from tools.config_reader import config
from _types.bot import WinterDragon

Commands = app_commands.AppCommand | app_commands.Command

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


    @staticmethod
    def is_group(check: Any) -> bool:
        return isinstance(check, app_commands.Group) 


    @staticmethod
    def is_subcommand(check: Any):
        return isinstance(check, app_commands.AppCommandGroup)


    def get_app_sub_command(self, command: Commands):
        # if subcommand is from parent command, return parent sub command combination early
        if not self.is_group(command.parent):
            raise CommandNotFound("Got AppCommand when expecting an SubCommand")
        
        if self.is_subcommand(command):
            return command, command.mention


    def get_app_command(self, command: Commands):
        if type(command) == app_commands.AppCommand:
            self.logger.debug(f"Quick return for {command.name}, already an AppCommand")
            return command
        
        if self.is_subcommand(command):
            raise CommandNotFound("Got a SubCommand when expecting an AppCommand")
