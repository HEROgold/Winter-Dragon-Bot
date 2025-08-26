"""Monitor and log webhook deletion events in Discord servers.

Track when users delete webhooks and generate appropriate audit logs.
"""
from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.constants import DELETED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent


class WebhookDelete(AuditEvent):
    """Process webhook deletion events in Discord guilds.

    Monitor the audit log for webhook deletions, log the events,
    and create notification embeds with relevant information.
    """

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.webhook_delete
        self.logger.debug(f"on webhook_delete: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        """Create an embed message for the webhook deletion event.

        This method generates a Discord embed object containing details about the deleted webhook,
        including the user who deleted it, the name of the webhook, the channel it was deleted from,
        and the reason for deletion.

        Returns:
            Embed: A Discord embed object with the webhook deletion details.

        Raises:
            TypeError: If the user is not a Discord user or the target is not a guild channel.

        """
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

        return Embed(
            title="Webhook Created",
            description=f"{user.mention} deleted webhook `{webhook_name}` in {channel.mention} with reason: {self.entry.reason}",  # noqa: E501
            color=DELETED_COLOR,
        )
