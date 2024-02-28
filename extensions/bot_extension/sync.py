import discord
from discord import app_commands
from discord.ext import commands

from _types.bot import WinterDragon
from _types.cogs import Cog
from tools.config_reader import config


class Sync(Cog):


    @app_commands.command(name="sync", description="Sync all commands on all servers (Bot dev only)")
    @app_commands.guilds(config.getint("Main", "support_guild_id"))
    @commands.is_owner()
    async def slash_sync(self, interaction: discord.Interaction) -> None:
        global_sync = await self.bot.tree.sync()
        guild = self.bot.get_guild(config.getint("Main", "support_guild_id"))
        local_sync = await self.bot.tree.sync(guild=guild)
        self.logger.warning(f"{interaction.user} Synced slash commands!")
        self.logger.debug(f"Synced commands: {global_sync=}, {local_sync=}")
        global_list = [command.name for command in global_sync]
        local_list = [command.name for command in local_sync]
        global_list.sort()
        local_list.sort()
        await interaction.response.send_message(f"Sync complete\nGlobally synced: {global_list}\nLocally synced: {local_list} to {guild}", ephemeral=True)


    @commands.hybrid_command(name="sync_ctx", description="Sync all commands on all servers (Bot dev only)")
    @commands.is_owner()
    async def slash_sync_hybrid(self, ctx: commands.Context) -> None:
        global_sync = await self.bot.tree.sync()
        guild = self.bot.get_guild(config.getint("Main", "support_guild_id"))
        local_sync = await self.bot.tree.sync(guild=guild)
        self.logger.warning(f"{ctx.author} Synced slash commands!")
        self.logger.debug(f"Synced commands: {global_sync=} {local_sync=}")
        global_list = [command.name for command in global_sync]
        local_list = [command.name for command in local_sync]
        global_list.sort()
        local_list.sort()
        await ctx.send(f"Sync complete\nGlobally synced: {global_list}\nLocally synced: {local_list} to {guild}")



async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Sync(bot))
