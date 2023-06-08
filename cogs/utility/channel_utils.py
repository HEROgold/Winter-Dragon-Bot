import logging

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config
from tools import app_command_tools


@app_commands.guild_only()
class ChannelUtils(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.act = app_command_tools.Converter(bot=self.bot)


    categories = app_commands.Group(name="categories", description="Manage your categories")

    @categories.command(
        name="delete",
        description="Delete a category and ALL channels inside."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slash_cat_delete(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        await interaction.response.defer(ephemeral=True)
        # _, cmd_mention = await self.act.get_app_sub_command(self.slash_cat_delete)
        for channel in category.channels:
            await channel.delete(reason=f"Deleted by {interaction.user.mention} using /channel-utils categories delete") # {cmd_mention}
        await category.delete(reason=f"Deleted by {interaction.user.mention} using /channel-utils categories delete") # {cmd_mention}
        try:
            await interaction.followup.send("Channel's removed", ephemeral=True)
        except discord.NotFound:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelUtils(bot)) # type: ignore
