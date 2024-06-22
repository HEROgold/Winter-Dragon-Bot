from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from _types.bot import WinterDragon
from _types.cogs import Cog


if TYPE_CHECKING:
    from discord.app_commands.models import AppCommand


class Sync(Cog):
    @app_commands.command(name="sync", description="Sync all commands on this server")
    async def slash_sync(self, interaction: discord.Interaction | commands.Context) -> None:
        user = interaction.author if isinstance(interaction, commands.Context) else interaction.user

        guild = interaction.guild

        local_sync = await self.bot.tree.sync(guild=guild)

        self.logger.warning(f"{user} Synced slash commands!")
        self.logger.debug(f"Synced commands: {local_sync}")
        local_list = [command.name for command in local_sync]
        local_list.sort()
        await interaction.response.send_message(f"Sync complete\nSynced: {local_list} to {guild}", ephemeral=True)


    @commands.is_owner()
    @commands.hybrid_command(name="sync_ctx", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync_hybrid(self, ctx: commands.Context) -> None:
        msg = "Synced commands: "

        global_sync = await self.bot.tree.sync()
        global_list = [command.name for command in global_sync]
        global_list.sort()
        msg += f"{global_list}"

        guild = ctx.guild

        local_sync: list[AppCommand] = []
        for guild in self.bot.guilds:
            local_sync += await self.bot.tree.sync(guild=guild)
            local_list = [command.name for command in local_sync]
            local_list.sort()
            msg += f" {local_sync} for {guild}"

        self.logger.warning(f"{ctx.author} Synced slash commands!")
        self.logger.debug(msg)
        await ctx.send(msg)



async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Sync(bot))
