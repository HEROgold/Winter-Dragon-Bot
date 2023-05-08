import logging

import discord
from discord import app_commands
from discord.ext import commands

import config

class Sync(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(name="sync", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync(self, interaction:discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        global_sync = await self.bot.tree.sync()
        guild = self.bot.get_guild(config.Main.SUPPORT_GUILD_ID)
        local_sync = await self.bot.tree.sync(guild=guild)
        self.logger.warning(f"{interaction.user} Synced slash commands!")
        self.logger.debug(f"Synced commands: global_commands={global_sync} guild_commands={local_sync}")
        global_list = [command.name for command in global_sync]
        local_list = [command.name for command in local_sync]
        global_list.sort()
        local_list.sort()
        await interaction.response.send_message(f"Sync complete\nGlobaly synced: {global_list}\nLocally synced: {local_list} to {guild}", ephemeral=True)


async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Sync(bot))
