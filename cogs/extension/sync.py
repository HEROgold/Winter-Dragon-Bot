import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands
import config

class Sync(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot=bot

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(2)
        logging.info("Syncing slash commands...")
        await self.bot.tree.sync()
        logging.info("Synced slash commands")

    @app_commands.command(name="sync", description="Sync slash commands for this server")
    async def slash_sync(self, interaction: discord.Interaction):
        if not interaction.permissions.administrator:
            interaction.response.send_message("No permissions to run this command", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self.bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send("Sync complete", ephemeral=True)

    @app_commands.command(name="sync_all", description="Sync all commands on all servers")
    async def slash_sync_all(self, interaction: discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            interaction.response.send_message("No permissions to run this command", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self.bot.tree.sync()
        await interaction.followup.send("Sync complete", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(Sync(bot))