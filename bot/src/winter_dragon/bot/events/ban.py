"""."""
from typing import override

from discord import Embed, Member, User
from sqlmodel import select
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings
from winter_dragon.database.constants import session
from winter_dragon.database.tables.sync_ban import SyncBanGuild, SyncBanUser


class Ban(AuditEvent):
    """Handle ban events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.ban
        self.logger.debug(f"on ban: {self.entry.guild=}, {self.entry=}")
        d_user = self.entry.target
        if not isinstance(d_user, User):
            self.logger.error(f"Ban target is not a User: {self.entry.target=}")
            return
        self.synchronize_ban(d_user)

    def synchronize_ban(self, d_user: User) -> None:
        """Synchronize the ban with the database."""
        if session.exec(
            select(SyncBanGuild).where(SyncBanGuild.guild_id == self.entry.guild.id),
        ).first() is not None:
            session.add(SyncBanUser(user_id=d_user.id))
            session.commit()


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(target, (User, Member)):
            msg = f"Target is not a discord user: {target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        return Embed(
            title="Ban",
            description=f"{user.mention} banned {target.mention} {target.name} with reason: {self.entry.reason}",
            color=Settings.deleted_color,
        )
