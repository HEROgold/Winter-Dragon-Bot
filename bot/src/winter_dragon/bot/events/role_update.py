"""."""
from typing import override

from discord import Embed, Member, Role, User
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class RoleUpdate(AuditEvent):
    """Handle role update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.role_update
        self.logger.debug(f"on role_update: {self.entry.guild=}, {self.entry.target=}")


    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        role = self.entry.target
        user = self.entry.user
        before = self.entry.before
        after = self.entry.after
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(role, Role):
            msg = f"Role is not a discord role: {role=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        properties = {
            "name",
            "color",
            "hoist",
            "mentionable",
            "permissions",
            "position",
        }

        differences = [
            prop
            for prop in properties
            if hasattr(before, prop) and getattr(before, prop) != getattr(after, prop)
        ]

        embed = Embed(
            title="Role Update",
            description=f"{user.mention} updated role {role.mention} with reason: {self.entry.reason}",
            color=CHANGED_COLOR,
        )

        # Add fields for each changed property
        for prop in differences:
            before_val = getattr(before, prop, None)
            after_val = getattr(after, prop, None)

            embed.add_field(
                name=f"{prop.replace('_', ' ').title()}",
                value=f"From: `{before_val}` → To: `{after_val}`",
                inline=False,
            )

        return embed
