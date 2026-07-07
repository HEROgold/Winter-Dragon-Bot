"""Discord guild model."""

from __future__ import annotations

from wd_discord.guild.emoji import Emoji
from wd_discord.guild.features import (
    DefaultMessageNotificationLevel,
    ExplicitContentFilterLevel,
    MFALevel,
    NSFWLevel,
    PremiumTier,
    SystemChannelFlags,
    VerificationLevel,
)
from wd_discord.guild.role import Role
from wd_discord.guild.sticker import Sticker
from wd_discord.guild.welcome_screen import WelcomeScreen
from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.snowflake import Snowflake


class Guild(DiscordModel):
    """https://docs.discord.com/developers/resources/guild#guild-object.

    The gateway ``GUILD_CREATE``-only fields are intentionally omitted (they are not returned by
    ``GET /guilds/{guild.id}``): voice_states, members, channels, threads, presences,
    stage_instances, guild_scheduled_events, and soundboard_sounds.
    """

    id: Snowflake
    """Guild id."""
    name: str # TODO: Make use of LimitedString? probably should expand that with min_length as well.
    """Guild name (2-100 characters, excluding trailing and leading whitespace)."""
    icon: ImageHash | None
    """Icon hash."""
    icon_hash: ImageHash | None = None
    """Icon hash, returned when in the template object."""
    splash: ImageHash | None
    """Splash hash."""
    discovery_splash: ImageHash | None
    """Discovery splash hash; only present for guilds with the DISCOVERABLE feature."""
    owner: bool | None = None
    """Whether the current user is the owner of the guild."""
    owner_id: Snowflake
    """Id of owner."""
    permissions: PermissionsField | None = None
    """Total permissions for the current user in the guild (excludes overwrites and implicit permissions)."""
    afk_channel_id: Snowflake | None
    """Id of afk channel."""
    afk_timeout: int
    """Afk timeout in seconds."""
    widget_enabled: bool | None = None
    """Whether the server widget is enabled."""
    widget_channel_id: Snowflake | None = None
    """The channel id that the widget will generate an invite to, or null if set to no invite."""
    verification_level: VerificationLevel
    """Verification level required for the guild."""
    default_message_notifications: DefaultMessageNotificationLevel
    """Default message notifications level."""
    explicit_content_filter: ExplicitContentFilterLevel
    """Explicit content filter level."""
    roles: list[Role]
    """Roles in the guild."""
    emojis: list[Emoji]
    """Custom guild emojis."""
    features: list[str]
    """Enabled guild features (kept as raw strings so unknown future features don't fail validation)."""
    mfa_level: MFALevel
    """Required MFA level for the guild."""
    application_id: Snowflake | None
    """Application id of the guild creator if it is bot-created."""
    system_channel_id: Snowflake | None
    """The id of the channel where guild notices such as welcome messages and boost events are posted."""
    system_channel_flags: SystemChannelFlags
    """System channel flags."""
    rules_channel_id: Snowflake | None
    """The id of the channel where Community guilds can display rules and/or guidelines."""
    max_presences: int | None = None
    """The maximum number of presences for the guild (null is always returned, apart from the largest of guilds)."""
    max_members: int | None = None
    """The maximum number of members for the guild."""
    vanity_url_code: str | None
    """The vanity url code for the guild."""
    description: str | None
    """The description of a guild."""
    banner: ImageHash | None
    """Banner hash."""
    premium_tier: PremiumTier
    """Premium tier (Server Boost level)."""
    premium_subscription_count: int | None = None
    """The number of boosts this guild currently has."""
    preferred_locale: str
    """The preferred locale of a Community guild; used in server discovery and notices from Discord."""
    public_updates_channel_id: Snowflake | None
    """The id of the channel where admins and moderators of Community guilds receive notices from Discord."""
    max_video_channel_users: int | None = None
    """The maximum amount of users in a video channel."""
    max_stage_video_channel_users: int | None = None
    """The maximum amount of users in a stage video channel."""
    approximate_member_count: int | None = None
    """Approximate number of members in this guild."""
    approximate_presence_count: int | None = None
    """Approximate number of non-offline members in this guild."""
    welcome_screen: WelcomeScreen | None = None
    """The welcome screen of a Community guild, shown to new members."""
    nsfw_level: NSFWLevel
    """Guild NSFW level."""
    stickers: list[Sticker] | None = None
    """Custom guild stickers."""
    premium_progress_bar_enabled: bool
    """Whether the guild has the boost progress bar enabled."""
    safety_alerts_channel_id: Snowflake | None # TODO: Could this Snowflake become Channel object? perhaps using a helper property instead is best.
    """The id of the channel where admins and moderators of Community guilds receive safety alerts from Discord."""
