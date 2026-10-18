"""The Discord invite resource."""

from __future__ import annotations

from pydantic import Field
lazy from wd_config.discord import URLS

from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.permissions import ChannelType
from wd_discord.resources.guild.features import NSFWLevel, VerificationLevel
from wd_discord.resources.user.user import User
from wd_discord.snowflake import Snowflake


class InviteGuild(DiscordModel):
    """The summary of a guild Discord sends inside an invite (https://docs.discord.com/developers/resources/invite#invite-object)."""

    id: Snowflake
    name: str | None = None
    splash: ImageHash | None = None
    banner: ImageHash | None = None
    description: str | None = None
    icon: ImageHash | None = None
    features: list[str] = Field(default_factory=list)
    """Kept as strings, so features Discord adds later don't fail validation."""
    verification_level: VerificationLevel | None = None
    vanity_url_code: str | None = None
    nsfw_level: NSFWLevel | None = None
    premium_subscription_count: int | None = None


class InviteChannel(DiscordModel):
    """The summary of a channel Discord sends inside an invite (https://docs.discord.com/developers/resources/invite#invite-object)."""

    id: Snowflake
    name: str | None = None
    type: ChannelType | None = None


class Invite(DiscordModel):
    """A guild invite (subset - https://docs.discord.com/developers/resources/invite).

    ``guild`` and ``channel`` arrive as summaries, not the full REST resources, so they have their own models.
    """

    code: str
    guild: InviteGuild | None = None
    channel: InviteChannel | None = None
    inviter: User | None = None
    uses: int | None = None
    max_uses: int | None = None
    max_age: int | None = None
    temporary: bool | None = None
    created_at: str | None = None

    @property
    def url(self) -> str:
        """The invite's shareable URL."""
        return f"{URLS.invite}/{self.code}"
