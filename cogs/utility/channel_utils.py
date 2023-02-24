# TODO: remove a guild category, AND ALL channels inside
import pickle
import logging
import os

import discord # type: ignore
from discord import app_commands
from discord.ext import commands

import config
import dragon_database

@app_commands.guild_only()
class ChannelUtils(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
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


    categories = app_commands.Group(name="categories", description="Manage your categories")

    @categories.command(
        name="delete",
        description="Delete a category and ALL channels inside."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slash_cat_delete(self, interaction:discord.Interaction, category:discord.CategoryChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        for channel in category.channels:
            await channel.delete()
        await category.delete()
        await interaction.followup.send("Channel's removed", ephemeral=True)

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(ChannelUtils(bot)) # type: ignore