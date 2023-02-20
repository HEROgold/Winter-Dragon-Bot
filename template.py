import json
import logging
import os

import discord # type: ignore
from discord import app_commands
from discord.ext import commands

import config
import dragon_database


class Temp(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        else:
            with open(self.DBLocation, "r") as f:
                data = json.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "w") as f:
                json.dump(data, f)

    # FIXME: seems to cause issues with loading cogs?
    async def cog_load(self) -> None:
        self.data = await self.get_data()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    @app_commands.command(
        name="TEMP",
        description="TEMP"
    )
    async def slash_TEMP(self) -> None:
        pass

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Temp(bot)) # type: ignore
