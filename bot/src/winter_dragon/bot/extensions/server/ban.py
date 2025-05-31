"""Logger mixin for database classes."""

import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.database.tables import SyncBanGuild, SyncBanUser


class SyncedBans(GroupCog):
    """Sync bans across all guilds that subscribe to this feature."""

    async def create_banned_role(self, guild: discord.Guild) -> discord.Role:
        """Create a role for banned users."""
        return await guild.create_role(
            name="Banned",
            permissions=discord.Permissions.none(),
        )

    @Cog.listener()
    async def on_ban(self, member: discord.Member) -> None:
        """When a member is banned, sync the ban across all guilds."""
        await self.synced_ban_sync(member)

    sync = app_commands.Group(
        name="sync",
        description="Synchronize bans across other servers",
    )

    @sync.command(name="join", description="Start syncing ban's with this guild")
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

    @sync.command(name="leave", description="Stop syncing ban's with this guild")
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
            self.session.exec(
                select(SyncBanGuild)
                .where(SyncBanGuild.guild_id == guild.id)).first(),
        )
        self.session.commit()

        await interaction.response.send_message(
            "This guild will no longer have ban's synced across this bot.",
            ephemeral=True,
        )

    async def synced_ban_sync(self, member: discord.Member) -> None:
            """Ban a member from all guilds that are synced."""
            self.session.add(
                SyncBanUser(
                    user_id=member.id,
                ),
            )

            for db_guild in self.session.exec(select(SyncBanGuild)).all():
                # Instead of banning the user, we should notify guild moderators/admins
                # that the user has been banned in another guild, warning them of the user.
                if guild := self.bot.get_guild(db_guild.guild_id):
                    await guild.ban(member, reason="Syncing bans")
            self.session.commit()


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(SyncedBans(bot=bot))
