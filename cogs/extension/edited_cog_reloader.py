import asyncio
import datetime
import json
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
import dragon_database


class AutoCogReloader(commands.GroupCog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = {
            "timestamp": datetime.datetime.now().timestamp(),
            "files": {},
            "edited" : {}
            }
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
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

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "w") as f:
                json.dump(data, f)

    async def cog_unload(self):
        await self.set_data(self.data)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.data["files"]:
            self.logger.info("Starting Auto Reloader.")
            await self.auto_reload()

    def get_cog_data(self) -> None:
        for root, subdirs, files in os.walk("cogs"):
            for file in files:
                if not file.endswith(".py"):
                    continue
                if file == os.path.basename(__file__):
                    # self.logger.debug(f"Skipping {file} (myself/itself)")
                    continue
                # self.logger.debug(f"Getting data from {file}")
                file_path = os.path.join(root, file)
                cog_path = os.path.join(root, file[:-3]).replace("\\", ".")
                with open(file_path, "r") as f:
                    edit_timestamp = os.path.getmtime(file_path)
                    self.data["files"][file] = {
                            "filepath": file_path,
                            "cog_path": cog_path,
                            "edit_time": edit_timestamp
                        }

    async def check_edits(self) -> None:
        files:dict = self.data["files"]
        self.get_cog_data()
        for file in files:
            start_time = self.data["timestamp"]
            edit_time = self.data["files"][file]["edit_time"]
            if start_time < edit_time:
                if file in self.data["edited"]:
                    continue
                self.logger.info(f"{file} has been edited!")
                self.data["edited"][file] = self.data["files"][file]
        # self.logger.debug(f"{self.data}")

    async def auto_reload(self) -> None:  # sourcery skip: useless-else-on-loop
        if not self.data["edited"]:
            await self.check_edits()
        for file_data in list(self.data["edited"]):
            await self.bot.reload_extension(self.data["edited"][file_data]["cog_path"])
            self.logger.info(f"Automatically reloaded {file_data}")
            del self.data["edited"][file_data]
        else:
            self.data["timestamp"] = datetime.datetime.now().timestamp()
        await asyncio.sleep(1)
        await self.auto_reload()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoCogReloader(bot))
