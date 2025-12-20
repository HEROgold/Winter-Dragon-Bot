"""Module to sync slash commands with the Discord API."""

from typing import TYPE_CHECKING, ClassVar

import discord
from discord import Guild, app_commands
from discord.ext import commands

from winter_dragon.bot.core.cogs import Cog


if TYPE_CHECKING:
    from discord.app_commands.models import AppCommand


class Sync(Cog, auto_load=True):
    """Sync slash commands with the Discord API."""

    COMMAND_DESCRIPTION_LIMIT: ClassVar[int] = 100
    COMMAND_NAME_LIMIT: ClassVar[int] = 32

    def _fix_invalid_commands(self) -> None:
        invalid_found = False
        for command in self.bot.tree.walk_commands():
            name_len = len(command.name)
            desc_len = len(command.description or "")
            if name_len > self.COMMAND_NAME_LIMIT:
                invalid_found = True
                self.logger.error(
                    "Command `%s` exceeds name limit (%s > %s)",
                    command.qualified_name,
                    name_len,
                    self.COMMAND_NAME_LIMIT,
                )
                self._fix_name(command)
            if desc_len > self.COMMAND_DESCRIPTION_LIMIT:
                invalid_found = True
                self.logger.error(
                    "Command `%s` exceeds description limit (%s > %s): %r",
                    command.qualified_name,
                    desc_len,
                    self.COMMAND_DESCRIPTION_LIMIT,
                    command.description,
                )
                self._fix_description(command)
            self.logger.debug(
                "Command `%s`: name=%s chars, description=%s chars",
                command.qualified_name,
                name_len,
                desc_len,
            )
        if not invalid_found:
            self.logger.debug("All commands satisfy current Discord limits.")

    def _fix_name(self, command: app_commands.Command | app_commands.Group) -> None:
        if len(command.name) > self.COMMAND_NAME_LIMIT:
            command.name = command.name[: self.COMMAND_NAME_LIMIT - 3] + "..."
            self.logger.info(
                    "Fixed name for command `%s` to fit within limit.",
                    command.qualified_name,
                )

    def _fix_description(self, command: app_commands.Command | app_commands.Group) -> None:
        if len(command.description or "") > self.COMMAND_DESCRIPTION_LIMIT:
            command.description = command.description[: self.COMMAND_DESCRIPTION_LIMIT - 3] + "..."
            self.logger.info(
                    "Fixed description for command `%s` to fit within limit.",
                    command.qualified_name,
                )

    @app_commands.command(name="sync", description="Sync all commands on this guild")
    async def slash_sync(self, interaction: discord.Interaction) -> None:
        """Sync all commands on the current guild."""
        self._fix_invalid_commands()
        await interaction.response.defer(ephemeral=True)
        user = interaction.author if isinstance(interaction, commands.Context) else interaction.user
        is_allowed = await self.bot.is_owner(user)

        if not is_allowed:
            msg = "You are not allowed to sync commands"
            self.logger.warning(f"{user} tried to sync commands, but is not allowed.")
            raise commands.NotOwner(msg)
        guild = interaction.guild

        local_sync = await self.bot.tree.sync(guild=guild)

        self.logger.warning(f"{user} Synced slash commands!")
        self.logger.debug(f"Synced commands: {local_sync}")
        local_list = [command.name for command in local_sync]
        local_list.sort()
        await interaction.followup.send(f"Sync complete\nSynced: {local_list} to {guild}")

    @commands.is_owner()
    @commands.hybrid_command(name="sync_ctx", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync_hybrid(self, ctx: commands.Context) -> None:
        """Sync all commands on all servers. This is a ctx and slash command (hybrid)."""
        self._fix_invalid_commands()
        msg = "Synced commands: "
        guild = ctx.guild

        msg += await self.sync_global()
        for guild in self.bot.guilds:
            msg += await self.sync_local(guild)

        self.logger.warning(f"{ctx.author} Synced slash commands!")
        self.logger.debug(msg)
        await ctx.send(msg, ephemeral=True)

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
