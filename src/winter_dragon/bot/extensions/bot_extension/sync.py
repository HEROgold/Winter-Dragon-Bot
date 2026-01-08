"""Module to sync slash commands with the Discord API."""


from logging import Logger
from typing import Protocol

import discord
from discord import Guild, app_commands
from discord.app_commands import ContextMenu
from discord.app_commands.models import AppCommand
from discord.ext import commands
from herogold.log import LoggerMixin

from winter_dragon.bot.core.cogs import Cog


COMMAND_DESCRIPTION_LIMIT = 100
COMMAND_NAME_LIMIT = 32

class CommandLike(Protocol):
    """Protocol for command like objects."""

    @property
    def name(self) -> str:
        """Command name."""
        ...
    @name.setter
    def name(self, value: str) -> None:
        """Set command name."""
        ...
    @property
    def qualified_name(self) -> str:
        """Fully qualified command name."""
        ...
    @property
    def description(self) -> str:
        """Command description."""
        ...
    @description.setter
    def description(self, value: str) -> None:
        """Set command description."""
        ...

def sync_name(command: CommandLike, logger: Logger) -> str:
    """Return the name used for syncing the command."""
    name_len = len(command.name)
    if name_len >= COMMAND_NAME_LIMIT:
        logger.critical("Command name too long: %s", command.qualified_name)
        logger.warning(
        "Fixing command name too long: %s (%d > %d)",
            command.qualified_name, name_len, COMMAND_NAME_LIMIT
        )
        return command.name[:COMMAND_NAME_LIMIT - 3] + "..."
    return command.name

def sync_description(command: CommandLike, logger: Logger) -> str:
    """Return the description used for syncing the command."""
    desc = command.description or ""
    desc_len = len(desc)
    if desc_len > COMMAND_DESCRIPTION_LIMIT:
        logger.warning(
            "Fixing command description too long: %s (%d > %d)",
            command.qualified_name, desc_len, COMMAND_DESCRIPTION_LIMIT
        )
        return desc[:COMMAND_DESCRIPTION_LIMIT - 3] + "..."
    return command.description

class LenFixer(LoggerMixin):
    """Context manager to temporarily fix command name/description length."""

    def __init__(self, tree: app_commands.CommandTree, guild: Guild | None = None) -> None:
        """Initialize the context manager."""
        self.tree = tree
        self.guild = guild
        self._stored_commands: list[tuple[CommandLike, str, str]] = []

    def _all_commands(self):  # noqa: ANN202
        """Get all commands and groups with their subcommands from the tree."""
        if self.guild:
            for cmd in self.tree.get_commands(guild=self.guild):
                yield cmd
                if isinstance(cmd, app_commands.Group):
                    yield from cmd.walk_commands()

        for cmd in self.tree.walk_commands():
            yield cmd

    def __enter__(self) -> None:
        """Enter the context manager."""
        for i in self._all_commands():
            old_name = i.name
            old_desc = i.description

            if (
                isinstance(i, ContextMenu)
                or len(i.name) < COMMAND_NAME_LIMIT
                or len(i.description) <= COMMAND_DESCRIPTION_LIMIT
            ):
                continue

            self._stored_commands.append((i, old_name, old_desc))
            i.name = sync_name(i, self.logger)
            i.description = sync_description(i, self.logger)

    def __exit__(self, *args: object) -> None:
        """Exit the context manager and restore original values."""
        for cmd, old_name, old_desc in self._stored_commands:
            self.logger.debug("Restoring command: %s", cmd.qualified_name)
            self.logger.debug("Restoring description: %s", old_desc)
            cmd.name = old_name
            cmd.description = old_desc
        self._stored_commands.clear()


class Sync(Cog, auto_load=True):
    """Sync slash commands with the Discord API."""

    @app_commands.command(name="sync", description="Sync all commands on this guild")
    async def slash_sync(self, interaction: discord.Interaction) -> None:
        """Sync all commands on the current guild."""
        await interaction.response.defer(ephemeral=True)
        user = interaction.author if isinstance(interaction, commands.Context) else interaction.user
        is_allowed = await self.bot.is_owner(user)

        if not is_allowed:
            msg = "You are not allowed to sync commands"
            self.logger.warning(f"{user} tried to sync commands, but is not allowed.")
            raise commands.NotOwner(msg)
        guild = interaction.guild

        if guild is None:
            msg = "This command can only be used in a guild."
            self.logger.warning(f"{user} tried to sync commands outside a guild.")
            raise commands.NoPrivateMessage(msg)

        local_sync = await self.sync_local(guild)

        self.logger.warning(f"{user} Synced slash commands!")
        self.logger.debug(f"Synced commands: {local_sync}")
        local_list = [command.name for command in local_sync]
        local_list.sort()
        await interaction.followup.send(f"Sync complete\nSynced: {local_list} to {guild}")

    @commands.is_owner()
    @commands.hybrid_command(name="sync_ctx", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync_hybrid(self, ctx: commands.Context) -> None:
        """Sync all commands on all servers. This is a ctx and slash command (hybrid)."""
        msg = "Synced commands: "
        guild = ctx.guild

        synced_commands = await self.sync_global()
        msg += "".join([i.name for i in synced_commands]) + "\n"
        for guild in self.bot.guilds:
            synced_commands = await self.sync_local(guild)
            msg += "".join([i.name for i in synced_commands]) + "\n"

        self.logger.warning(f"{ctx.author} Synced slash commands!")
        self.logger.debug(msg)
        await ctx.send(msg, ephemeral=True)

    async def sync_local(self, guild: Guild) -> list[AppCommand]:
        """Sync all commands on a specific guild."""
        local_sync: list[AppCommand] = []
        with LenFixer(self.bot.tree, guild=guild):
            local_sync += await self.bot.tree.sync(guild=guild)
        local_list = [command.name for command in local_sync]
        local_list.sort()
        return local_sync

    async def sync_global(self) -> list[AppCommand]:
        """Sync all globally available commands."""
        with LenFixer(self.bot.tree):
            return await self.bot.tree.sync()
