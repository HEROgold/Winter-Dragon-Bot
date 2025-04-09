"""Module to sync slash commands with the Discord API."""
from typing import TYPE_CHECKING

import discord
from discord import Guild, app_commands
from discord.ext import commands
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog


if TYPE_CHECKING:
    from discord.app_commands.models import AppCommand


class Sync(Cog):
    """Sync slash commands with the Discord API."""

    @app_commands.command(name="sync", description="Sync all commands on this guild")
    async def slash_sync(self, interaction: discord.Interaction) -> None:
        """Sync all commands on the current guild."""
        user = interaction.author if isinstance(interaction, commands.Context) else interaction.user
        is_allowed = await self.bot.is_owner(user)

        if not is_allowed:
            msg = "You are not allowed to sync commands"
            raise commands.NotOwner(msg)
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
        """Sync all commands on all servers. This is a ctx and slash command (hybrid)."""
        msg = "Synced commands: "
        guild = ctx.guild

        msg += await self.sync_global()
        for guild in self.bot.guilds:
            msg += await self.sync_local(guild)

        self.logger.warning(f"{ctx.author} Synced slash commands!")
        self.logger.debug(msg)
        await ctx.send(msg)

    async def sync_local(self, guild: Guild) -> str:
        """Sync all commands on a specific guild."""
        local_sync: list[AppCommand] = []
        local_sync += await self.bot.tree.sync(guild=guild)
        local_list = [command.name for command in local_sync]
        local_list.sort()
        return f"{local_list} for {guild}\n"

    async def sync_global(self) -> str:
        """Sync all globally available commands."""
        global_sync = await self.bot.tree.sync()
        global_list = [command.name for command in global_sync]
        global_list.sort()
        return f"{global_list}\n"



async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Sync(bot))
