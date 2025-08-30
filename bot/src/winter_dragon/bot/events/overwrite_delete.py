"""."""
from typing import override

from discord import Embed, Member, Role, User
from discord.abc import GuildChannel
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class OverwriteDelete(AuditEvent):
    """Handle permission overwrite delete events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.overwrite_delete
        self.logger.debug(f"on overwrite_delete: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        user = self.entry.user
        channel = self.entry.target
        permissions = self.entry.extra
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(channel, GuildChannel):
            msg = f"Target is not a discord channel: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(permissions, (Role, Member)):
            msg = f"Permissions is not a discord role or member: {self.entry.extra=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        channel_mention = channel.mention
        target_mention = permissions.mention

        return Embed(
            title="Permission Overwrite Deleted",
            description=f"{user.mention} deleted permission overwrite for {target_mention} in {channel_mention} with reason: {self.entry.reason}",  # noqa: E501
            color=Settings.deleted_color,
        )
