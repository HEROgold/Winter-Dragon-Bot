import logging
import os
import pickle

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config
from tools import dragon_database


class Temp(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(
            f"{config.Main.BOT_NAME}.{self.__class__.__name__}"
        )
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    # TODO: Change/add get_data and set_data to use sql (exapmle?)
    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        self.data = await self.get_data()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    # TEMP_GROUP = app_commands.Group(name="TEMPGroup", description="TEMP")
    # @TEMP_GROUP.command()

    @app_commands.command(name="TEMP", description="TEMP")
    async def slash_TEMP(selfself, interaction: discord.Interaction) -> None:
        pass

    @slash_TEMP.autocomplete("")
    async def COMMAND_autocoplete_VARIABLE(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in []
            if current.lower() in i.lower()
        ]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Temp(bot))  # type: ignore
