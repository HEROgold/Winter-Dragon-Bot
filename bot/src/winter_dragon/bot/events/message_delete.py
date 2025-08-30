"""."""
from typing import cast, override

from discord import Embed, Member, Message, User
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class MessageDelete(AuditEvent):
    """Handle message delete events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.message_delete
        if not isinstance(self.entry.target, Message):
            self.logger.warning(f"Target is not a message: {type(self.entry.target)}")
            return

        message = cast("Message", self.entry.target)
        self.logger.debug(f"Message deleted: {message.guild=}, {message.channel=}, {message.clean_content=}")


    @override
    def create_embed(self) -> Embed:
        if not isinstance(self.entry.target, Message):
            self.logger.warning(f"Target is not a message: {type(self.entry.target)}")
            return Embed(
                title="Message Deleted",
                description="A message was deleted, but details could not be determined.",
                color=Settings.deleted_color,
            )

        message = cast("Message", self.entry.target)
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        description = f"Deleted message sent by {message.author.mention} with reason: {self.entry.reason}"
        embed = Embed(
            title="Message Deleted",
            description=description,
            color=Settings.deleted_color,
        )

        if hasattr(message, "clean_content") and message.clean_content:
            embed.add_field(
                name="Content",
                value=f"`{message.clean_content}`",
            )

        return embed
