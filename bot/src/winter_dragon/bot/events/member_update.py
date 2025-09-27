"""."""
from typing import override

from discord import AuditLogAction, Embed, Member, User
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.events.base.util import add_differences_to_embed
from winter_dragon.bot.settings import Settings


class MemberUpdate(AuditEvent, action=AuditLogAction.member_update):
    """Handle member update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.member_update
        self.logger.debug(f"on member_update: {self.entry.guild=}, {self.entry.target=}")


    @override
    def create_embed(self) -> Embed:
        target = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(target, (User, Member)):
            msg = f"Target is not a discord user: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        embed = Embed(
            title="Member Update",
            description=f"{user.mention} updated {target.mention} with reason: {self.entry.reason}",
            color=Settings.changed_color,
        )
        properties = {
            "nick",
            "mute",
            "deaf",
            "timed_out_until",
        }
        add_differences_to_embed(embed, self.entry, properties)
        return embed
