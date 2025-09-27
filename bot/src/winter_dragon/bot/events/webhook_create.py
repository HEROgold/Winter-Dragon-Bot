"""Monitor and log webhook creation events in Discord servers.

Track when users create new webhooks and generate appropriate audit logs.
"""
from typing import override

from discord import AuditLogAction, Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.settings import Settings


class WebhookCreate(AuditEvent, action=AuditLogAction.webhook_create):
    """Process webhook creation events in Discord guilds.

    Monitor the audit log for webhook creations, log the events,
    and create notification embeds with relevant information.
    """

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.webhook_create
        self.logger.debug(f"on webhook_create: {self.entry.guild=}, {self.entry=}")


    @override
    def create_embed(self) -> Embed:
        """Create an embed message for the webhook creation event.

        This method generates a Discord embed object containing details about the webhook creation,
        including the user who created the webhook, the name of the webhook, the channel it was created in,
        and the reason provided for its creation.

        Returns:
            Embed: A Discord embed object with the webhook creation details.

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
            description=f"{user.mention} created webhook `{webhook_name}` in {channel.mention} with reason: {self.entry.reason}",  # noqa: E501
            color=Settings.created_color,
        )
