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


class AutoCogReloader(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
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

    def setup_json(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME} Json Loaded.")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.data["files"]:
            self.logger.info("Starting Auto Reloader.")
            while True:
                await self.auto_reload()
                await asyncio.sleep(2)

    def get_cog_data(self) -> None:
        for root, _, files in os.walk("cogs"):
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
                            "filepath": f.name,
                            "cog_path": cog_path,
                            "edit_time": edit_timestamp
                        }

    async def check_edits(self) -> None:
        files = self.data["files"]
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

class CogsC(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
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

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    async def get_cogs(self) -> list[str]:
        extensions = []
        for root, _, files in os.walk("cogs"):
            extensions.extend(
                os.path.join(root, file[:-3]).replace("\\", ".")
                for file in files
                if file.endswith(".py")
            )
        return extensions

    async def mass_reload(self, interaction:discord.Interaction) -> None:
        reload_message = ""
        cogs = await self.get_cogs()
        for cog in cogs:
            try:
                await self.bot.reload_extension(cog)
            except Exception as e:
                self.logger.exception(f"Error while reloading {cog}: error=`{e}`")
            self.logger.info(f"Reloaded {cog}")
            reload_message += f"Reloaded {cog}\n"
        await interaction.followup.send(f"{reload_message}Restart complete.")

    @app_commands.command(
        name = "show",
        description = "Show loaded cogs (For bot developer only)"
        )
    async def slash_show_cogs(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        cogs = await self.get_cogs()
        self.logger.debug(f"Showing {cogs} to {interaction.user}")
        await interaction.response.send_message(f"{cogs}", ephemeral=True)

    @app_commands.command(
        name = "reload",
        description = "Reload a specified or all available cogs (For bot developer only)"
        )
    async def slash_restart(self, interaction:discord.Interaction, extension:str=None) -> None: # type: ignore
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer()
        if extension is None:
            await self.mass_reload(interaction)
        else:
            try:
                await self.bot.reload_extension(extension)
                self.logger.info(f"Reloaded {extension}")
                await interaction.followup.send(f"Reloaded {extension}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"error reloading {extension}", ephemeral=True)

    @slash_restart.autocomplete("extension")
    async def restart_autocomplete_extension(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in self.bot.extensions
            if current.lower() in extension.lower()
        ]

    @app_commands.command(
        name = "unload",
        description = "Unload a specified cog (For bot developer only)"
        )
    async def slash_unload(self, interaction:discord.Interaction, extension:str) -> None:
        if not self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        if extension is None:
            await interaction.followup.send("Please provide a cog to unload.", ephemeral=True)
        else:
            try:
                await self.bot.unload_extension(extension)
                self.logger.info(f"Unloaded {extension}")
                await interaction.followup.send(f"Unloaded {extension}", ephemeral=True)
            except Exception:
                self.logger.exception(f"unable to unload {extension}")
                await interaction.followup.send(f"Unable to unload {extension}", ephemeral=True)

    @slash_unload.autocomplete("extension")
    async def unload_autocomplete_extension(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in self.bot.extensions
            if current.lower() in extension.lower()
        ]

    @app_commands.command(
        name = "load",
        description = "Load a specified or all available cogs (For bot developer only)"
        )
    async def slash_load(self, interaction:discord.Interaction, extension:str) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.load_extension(extension)
            self.logger.info(f"Loaded {extension}")
            await interaction.followup.send(f"Loaded {extension}", ephemeral=True)
        except Exception:
            self.logger.exception(f"unable to load {extension}")
            await interaction.followup.send(f"Unable to load {extension}", ephemeral=True)

    @slash_load.autocomplete("extension")
    async def load_autocomplete_extension(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        cogs = await self.get_cogs()
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in cogs
            if current.lower() in extension.lower()
        ]

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoCogReloader(bot))
    await bot.add_cog(CogsC(bot))
