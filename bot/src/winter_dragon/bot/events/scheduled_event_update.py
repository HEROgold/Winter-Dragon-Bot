"""."""
from typing import override

from discord import Embed, Member, User
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class ScheduledEventUpdate(AuditEvent):
    """Handle scheduled event update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.scheduled_event_update
        self.logger.debug(f"on scheduled_event_update: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        event = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        before = getattr(self.entry, "before", {})
        after = getattr(self.entry, "after", {})

        properties = {
            "name",
            "description",
            "channel_id",
            "entity_type",
            "status",
            "location",
            "privacy_level",
            "scheduled_start_time",
            "scheduled_end_time",
        }

        differences = [
            prop
            for prop in properties
            if hasattr(before, prop) and getattr(before, prop) != getattr(after, prop)
        ]

        event_name = getattr(event, "name", str(event))

        embed = Embed(
            title="Scheduled Event Update",
            description=f"{user.mention} updated scheduled event `{event_name}` with reason: {self.entry.reason}",
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

