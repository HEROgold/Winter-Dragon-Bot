"""Discord guild member model (https://docs.discord.com/developers/resources/guild#guild-member-object)."""

from __future__ import annotations

from datetime import datetime
lazy from enum import IntFlag

from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.resources.user.collectibles import Collectibles
from wd_discord.resources.user.profile import Avatar
from wd_discord.resources.user.user import User
from wd_discord.snowflake import Snowflake


class GuildMemberFlags(IntFlag):
    """https://docs.discord.com/developers/resources/guild#guild-member-object-guild-member-flags."""

    DID_REJOIN = 1 << 0
    """Member has left and rejoined the guild."""
    COMPLETED_ONBOARDING = 1 << 1
    """Member has completed onboarding."""
    BYPASSES_VERIFICATION = 1 << 2
    """Member is exempt from guild verification requirements."""
    STARTED_ONBOARDING = 1 << 3
    """Member has started onboarding."""
    IS_GUEST = 1 << 4
    """Member is a guest and can only access the voice channel they were invited to."""
    STARTED_HOME_ACTIONS = 1 << 5
    """Member has started Server Guide new member actions."""
    COMPLETED_HOME_ACTIONS = 1 << 6
    """Member has completed Server Guide new member actions."""
    AUTOMOD_QUARANTINED_USERNAME = 1 << 7
    """Member's username, display name, or nickname is blocked by AutoMod."""
    DM_SETTINGS_UPSELL_ACKNOWLEDGED = 1 << 9
    """Member has dismissed the DM settings upsell."""
    AUTOMOD_QUARANTINED_GUILD_TAG = 1 << 10
    """Member's guild tag is blocked by AutoMod."""


class GuildMember(DiscordModel):
    """https://docs.discord.com/developers/resources/guild#guild-member-object."""

    user: User | None = None
    """The user this guild member represents; omitted in MESSAGE_CREATE and MESSAGE_UPDATE events."""
    nick: str | None = None
    """This user's guild nickname."""
    avatar: ImageHash | None = None
    """The member's guild avatar hash."""
    banner: ImageHash | None = None
    """The member's guild banner hash."""
    roles: list[Snowflake]
    """IDs of the roles this member has."""
    joined_at: datetime | None
    """When the user joined the guild; null for guest members."""
    premium_since: datetime | None = None
    """When the user started boosting the guild."""
    deaf: bool
    """Whether the user is deafened in voice channels."""
    mute: bool
    """Whether the user is muted in voice channels."""
    flags: GuildMemberFlags = GuildMemberFlags(0)
    """Guild member flags as a bit set."""
    pending: bool | None = None
    """Whether the user has not yet passed the guild's Membership Screening requirements."""
    permissions: PermissionsField | None = None
    """Total permissions of the member in the channel, including overwrites; only sent in interactions."""
    communication_disabled_until: datetime | None = None
    """When the user's timeout will expire; ``None`` or a past time when not timed out."""
    avatar_decoration_data: Avatar | None = None
    """Data for the member's guild avatar decoration."""
    collectibles: Collectibles | None = None
    """Data for the member's collectibles."""
