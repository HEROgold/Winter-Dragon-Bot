"""."""
from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.events.base.util import add_differences_to_embed
from winter_dragon.bot.settings import Settings


class ChannelUpdate(AuditEvent):
    """Handle channel update events."""

    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_update
        self.logger.debug(f"On channel update: {self.entry.guild=}, {self.entry.target=}")

    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        channel = self.entry.target
        user = self.entry.user

        if not isinstance(channel, GuildChannel):
            msg = f"Channel is not a guild channel: {channel=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)

        properties = {
            "name",
            "type",
            "position",
            "overwrites",
            "topic",
            "bitrate",
            "rtc_region",
            "video_quality_mode",
            "default_auto_archive_duration",
            "nsfw",
            "slowmode_delay",
            "user_limit",
        }

        embed= Embed(
            title="Channel Changed",
            description=(
                f"{user.mention} changed {channel.mention} with reason: {self.entry.reason}"
            ),
            color=Settings.changed_color,
        )
        add_differences_to_embed(embed, self.entry, properties)
        return embed
