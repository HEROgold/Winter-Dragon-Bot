"""Logger mixin for database classes."""

import discord
from discord import app_commands
from sqlmodel import select

from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.database.tables import SyncBanGuild, SyncBanUser
from winter_dragon.database.tables.guild import Guilds
from winter_dragon.database.tables.sync_ban.sync_ban_banned_by import SyncBanBannedBy
from winter_dragon.database.tables.user import Users


class SyncedBans(GroupCog, auto_load=True):
    """Sync bans across all guilds that subscribe to this feature."""

    async def create_banned_role(self, guild: discord.Guild) -> discord.Role:
        """Create a role for banned users."""
        return await guild.create_role(
            name="Banned",
            permissions=discord.Permissions.none(),
        )

    sync = app_commands.Group(
        name="sync",
        description="Synchronize bans across other servers",
    )

    @sync.command(name="join", description="Start syncing ban's with other guilds.")
    async def slash_synced_ban_join(self, interaction: discord.Interaction) -> None:
        """Start syncing ban's with this guild."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used in a guild.",
                ephemeral=True,
            )
            return

        self.session.add(
            SyncBanGuild(
                guild_id=guild.id,
            ),
        )
        self.session.commit()

        await interaction.response.send_message(
            "This guild will have ban's synced across this bot.",
            ephemeral=True,
        )

    @sync.command(name="leave", description="Stop syncing ban's with other guilds.")
    async def slash_synced_ban_leave(self, interaction: discord.Interaction) -> None:
        """Stop syncing ban's with this guild."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used in a guild.",
                ephemeral=True,
            )
            return

        self.session.delete(
            self.session.exec(select(SyncBanGuild).where(SyncBanGuild.guild_id == guild.id)).first(),
        )
        self.session.commit()

        await interaction.response.send_message(
            "This guild will no longer have ban's synced across other guilds.",
            ephemeral=True,
        )

    @sync.command(name="sync", description="Ban members banned from other synced guilds.")
    async def slash_synced_ban_sync(self, interaction: discord.Interaction) -> None:
        """Ban all members from all guilds that are synced."""
        query = (
            select(SyncBanBannedBy, Users, Guilds)
            .join(SyncBanUser)
            .join(Users)
            .join(SyncBanGuild)
            .join(Guilds)
            .where(SyncBanUser.user_id == Users.id, SyncBanGuild.guild_id == Guilds.id)
        )
        for result in self.session.exec(query).all():
            reason, user, db_guild = result
            target_guild = self.bot.get_guild(db_guild.id)
            if target_guild is None:
                self.logger.warning(f"Guild with ID {db_guild.id} not found in bot guilds.")
                continue
            member = target_guild.get_member(user.id)
            if member is None:
                self.logger.warning(f"Member with ID {user.id} not found in guild {target_guild.name}.")
                continue
            await target_guild.ban(
                member,
                reason=(
                    f"Syncing bans: {reason or 'No reason provided'} "
                    f"from {interaction.guild.name if interaction.guild else 'Unknown Guild'}"
                ),
            )
