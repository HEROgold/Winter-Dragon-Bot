from typing import override

from discord import Embed, Member, User
from discord.abc import GuildChannel
from winter_dragon.bot.constants import CHANGED_COLOR
from winter_dragon.bot.events.base.audit_event import AuditEvent
from winter_dragon.bot.events.base.util import get_differences


class ChannelUpdate(AuditEvent):
    @override
    async def handle(self) -> None:
        # https://discordpy.readthedocs.io/en/stable/api.html?highlight=auditlogentry#discord.AuditLogAction.channel_update
        self.logger.debug(f"On channel update: {self.entry.guild=}, {self.entry.target=}")

    @override
    def create_embed(self) -> Embed:  # sourcery skip: extract-duplicate-method
        channel = self.entry.target
        before = self.entry.before
        after = self.entry.after
        user = self.entry.user

        if not isinstance(channel, GuildChannel):
            msg = f"Channel is not a guild channel: {channel=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(user, (User, Member)):
            msg = f"User is not a discord user: {user=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(before, GuildChannel):
            msg = f"Before is not a guild channel: {before=}"
            self.logger.warning(msg)
            raise TypeError(msg)
        if not isinstance(after, GuildChannel):
            msg = f"After is not a guild channel: {after=}"
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

        channel_name = None
        if (
            (differences := get_differences(self.entry, properties))
            and ("name" in differences or before.name != after.name)
        ):
            channel_name = f"`{before.name}` to `{after.name}` for {channel.mention}"

        return Embed(
            title="Channel Changed",
            description=(
                f"{user.mention} changed {differences} of channel "
                f"{channel_name or after.mention} with reason: {self.entry.reason}"
            ),
            color=CHANGED_COLOR,
        )
