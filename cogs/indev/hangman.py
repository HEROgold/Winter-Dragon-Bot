import logging
import os
import pickle

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config
from tools.database_tables import ResultMassiveMultiplayer as ResultMM
from tools.database_tables import Lobby, Game, Session, engine


class Hangman(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./database/{self.DATABASE_NAME}.pkl"
            self.setup_pkl_file()

    def setup_pkl_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    # Hangman_GROUP = app_commands.Group(name="HangmanGroup", description="Hangman")
    # @Hangman_GROUP.command()

    # @app_commands.command(name="hangman", description="Hangman")
    # async def slash_Hangman(self, interaction: discord.Interaction) -> None:
    #     """Hangman"""
    #     raise NotImplementedError("Empty command")

    # @slash_Hangman.autocomplete("")
    # async def COMMAND_autocoplete_VARIABLE(
    #     self, interaction: discord.Interaction, current: str
    # ) -> list[app_commands.Choice[str]]:
    #     return [
    #         app_commands.Choice(name=i, value=i)
    #         for i in []
    #         if current.lower() in i.lower()
    #     ]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Hangman(bot))  # type: ignore
