import json
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database


class Temp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger("winter_dragon.TEMP")
        self.DATABASE_NAME = "TEMP"
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                self.logger.debug(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.debug(f"{self.DATABASE_NAME} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        else:
            with open(self.DBLocation, "r") as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "w") as f:
                json.dump(data, f)


async def setup(bot: commands.Bot):
    await bot.add_cog(Temp(bot))
