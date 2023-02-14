import logging

import discord
from discord import app_commands
from discord.ext import commands

import config

# FIXME: Sync command gets synced to only the correct guild,
# however all other @app_commands.guilds() decorators are synced globaly..
class Sync(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")

    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(name="sync", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync_all(self, interaction:discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        await interaction.response.defer(ephemeral=True)
        global_sync = await self.bot.tree.sync()
        local_sync = await self.bot.tree.sync(guild=self.bot.get_guild(config.Main.SUPPORT_GUILD_ID))
        self.logger.info(f"Synced slash commands: global_commands={global_sync} guild_commands={local_sync}")
        await interaction.followup.send("Sync complete", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(Sync(bot))
