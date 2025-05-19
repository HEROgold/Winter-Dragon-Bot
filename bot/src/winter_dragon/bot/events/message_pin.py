"""."""

from typing import override

from discord import Embed, Member, Message, TextChannel, User
from winter_dragon.bot.constants import CREATED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class MessagePin(AuditEvent):
    """Handle message pin events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.message_pin
        self.logger.debug(f"on message_pin: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        message = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(message, Message):
            msg = f"Target is not a discord message: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        channel = message.channel

        if not isinstance(channel, TextChannel):
            msg = f"Target is not a discord channel: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        author = message.author
        embed = Embed(
            title="Message Pinned",
            description=f"{user.mention} pinned a message from {author.mention} in {channel.mention} with reason: {self.entry.reason}",  # noqa: E501
            color=CREATED_COLOR,
        )
        embed.add_field(
            name="Content",
            value=f"`{message.clean_content}`",
            inline=False,
        )

        return embed

