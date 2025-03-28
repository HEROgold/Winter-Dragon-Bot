import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog, GroupCog
from winter_dragon.database.tables import SyncBanGuild, SyncBanUser


class SyncedBans(GroupCog):
    def get_seconds(self, seconds: int, minutes: int, hours: int, days: int) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds

    async def create_banned_role(self, guild: discord.Guild) -> discord.Role:
        return await guild.create_role(
            name="Banned",
            permissions=discord.Permissions.none(),
        )

    @Cog.listener()
    async def on_ban(self, member: discord.Member) -> None:
        await self.synced_ban_sync(member)

    sync = app_commands.Group(
        name="sync",
        description="Synchronize bans across other servers",
    )

    @sync.command(name="join", description="Start syncing ban's with this guild")
    async def slash_synced_ban_join(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        with self.session as session:
            session.add(
                SyncBanGuild(
                    guild_id=guild.id,
                ),
            )
            session.commit()

        await interaction.response.send_message(
            "This guild will have ban's synced across this bot.",
            ephemeral=True,
        )

    @sync.command(name="leave", description="Stop syncing ban's with this guild")
    async def slash_synced_ban_leave(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        with self.session as session:
            session.delete(
                session.exec(select(SyncBanGuild).where(SyncBanGuild.guild_id == guild.id)).first(),
            )
            session.commit()

        await interaction.response.send_message(
            "This guild will no longer have ban's synced across this bot.",
            ephemeral=True,
        )

    async def synced_ban_sync(self, member: discord.Member) -> None:
        with self.session as session:
            session.add(
                SyncBanUser(
                    user_id=member.id,
                ),
            )

            for db_guild in session.exec(select(SyncBanGuild)).all():
                guild = self.bot.get_guild(db_guild.guild_id)
                await guild.ban(member, reason="Syncing bans")
            session.commit()


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(SyncedBans(bot))
