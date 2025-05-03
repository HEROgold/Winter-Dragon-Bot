from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class ChannelCreate(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_create
        self.logger.debug(f"On channel create: {self.entry.guild=}, {self.entry.target=}")

    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        channel = self.entry.target
        if not isinstance(channel, GuildChannel):
            msg = f"Channel is not a guild channel: {channel=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        mention = channel.mention
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        return Embed(
            title="Channel Created",
            description=f"{user.mention} created {channel.type} {mention} with reason: {self.entry.reason}",
            color=CREATED_COLOR,
        )
