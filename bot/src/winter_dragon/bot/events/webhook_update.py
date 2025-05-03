from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.events.base.util import add_differences_to_embed


class WebhookUpdate(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.webhook_update
        self.logger.debug(f"on webhook_update: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        webhook = self.entry.target
        user = self.entry.user
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        webhook_name = getattr(webhook, "name", str(webhook))
        channel = getattr(webhook, "channel", None)

        if not isinstance(channel, GuildChannel):
            msg = f"Target is not a guild channel: {self.entry.target=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        embed = Embed(
            title="Webhook Created",
            description=f"{user.mention} updated webhook `{webhook_name}` in {channel.mention} with reason: {self.entry.reason}",  # noqa: E501
            color=CHANGED_COLOR,
        )
        add_differences_to_embed(embed, self.entry, ("name", "channel", "avatar"))
        return embed
