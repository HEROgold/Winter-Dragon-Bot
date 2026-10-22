"""Presences and activities as the gateway sends them (https://docs.discord.com/developers/events/gateway-events#presence).

Data only; :class:`~wd_discord.entities.presence.Presence` binds a presence to the client. Types are imported eagerly
because pydantic resolves field annotations at class-definition time.
"""

from __future__ import annotations

from enum import IntFlag

from wd_discord.color import Color
from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.open_enum import OpenIntEnum, OpenStrEnum
from wd_discord.resources.user.collectibles import Collectibles
from wd_discord.resources.user.profile import Avatar, DisplayNameStyles
from wd_discord.resources.user.user import UserPrimaryGuild
from wd_discord.snowflake import Snowflake


class Status(OpenStrEnum):
    """Valid presence statuses (https://docs.discord.com/developers/topics/gateway-events#update-presence-status-types)."""

    online = "online"
    dnd = "dnd"
    idle = "idle"
    invisible = "invisible"
    offline = "offline"


class ActivityType(OpenIntEnum):
    """https://docs.discord.com/developers/events/gateway-events#activity-object-activity-types."""

    PLAYING = 0
    STREAMING = 1
    LISTENING = 2
    WATCHING = 3
    CUSTOM = 4
    COMPETING = 5


class ActivityFlags(IntFlag):
    """https://docs.discord.com/developers/events/gateway-events#activity-object-activity-flags."""

    INSTANCE = 1 << 0
    JOIN = 1 << 1
    SPECTATE = 1 << 2
    JOIN_REQUEST = 1 << 3
    SYNC = 1 << 4
    PLAY = 1 << 5
    PARTY_PRIVACY_FRIENDS = 1 << 6
    PARTY_PRIVACY_VOICE_CHANNEL = 1 << 7
    EMBEDDED = 1 << 8


class ActivityTimestamps(DiscordModel):
    """When an activity started and ends, as Unix milliseconds."""

    start: int | None = None
    end: int | None = None


class ActivityEmoji(DiscordModel):
    """The emoji of a custom status."""

    name: str
    id: Snowflake | None = None
    animated: bool | None = None


class ActivityParty(DiscordModel):
    """The party a user is in for an activity."""

    id: str | None = None
    size: tuple[int, int] | None = None
    """The party's ``(current_size, max_size)``."""


class ActivityAssets(DiscordModel):
    """The images an activity shows, with their hover texts."""

    large_image: str | None = None
    large_text: str | None = None
    large_url: str | None = None
    small_image: str | None = None
    small_text: str | None = None
    small_url: str | None = None
    invite_cover_image: str | None = None


class ActivitySecrets(DiscordModel):
    """The secrets for joining or spectating an activity."""

    join: str | None = None
    spectate: str | None = None
    match: str | None = None


class Activity(DiscordModel):
    """https://docs.discord.com/developers/events/gateway-events#activity-object."""

    name: str
    type: ActivityType
    url: str | None = None
    created_at: int
    """When the activity was added to the user's session, as Unix milliseconds."""
    timestamps: ActivityTimestamps | None = None
    application_id: Snowflake | None = None
    status_display_type: int | None = None
    details: str | None = None
    details_url: str | None = None
    state: str | None = None
    state_url: str | None = None
    emoji: ActivityEmoji | None = None
    party: ActivityParty | None = None
    assets: ActivityAssets | None = None
    secrets: ActivitySecrets | None = None
    instance: bool | None = None
    flags: ActivityFlags | None = None
    buttons: list[str] | None = None
    """The labels of the activity's buttons; bots can't read where they link."""
    id: str | None = None
    """The activity's id within the user's session (``custom`` for a custom status). Sent by Discord, but not documented."""
    session_id: str | None = None
    """Sent by Discord, but not documented."""
    sync_id: str | None = None
    """For Spotify, the track's ID. Sent by Discord, but not documented."""
    platform: str | None = None
    """Sent by Discord, but not documented."""
    official_game_id: object | None = None
    """Sent by Discord, but not documented."""
    content_classification: dict[str, object] | None = None
    """Sent by Discord, but not documented."""


class ClientStatus(DiscordModel):
    """A user's status per platform; a platform they're offline or invisible on is left out."""

    desktop: Status | None = None
    mobile: Status | None = None
    web: Status | None = None
    vr: Status | None = None
    embedded: Status | None = None
    """The status in an embedded app (such as an Activity). Sent by Discord, but not documented."""


class PresenceUser(DiscordModel):
    """The user a presence is for: only ``id`` is certain, any other user field may come along."""

    id: Snowflake
    username: str | None = None
    discriminator: str | None = None
    global_name: str | None = None
    avatar: ImageHash | None = None
    bot: bool | None = None
    system: bool | None = None
    banner: ImageHash | None = None
    accent_color: Color | None = None
    flags: int | None = None
    public_flags: int | None = None
    avatar_decoration_data: Avatar | None = None
    collectibles: Collectibles | None = None
    primary_guild: UserPrimaryGuild | None = None
    display_name: str | None = None
    """The name shown for the user. Sent by Discord, but not documented; ``global_name`` is the documented field."""
    display_name_styles: DisplayNameStyles | None = None
    """How the display name is drawn. Sent by Discord, but not documented."""
    clan: object | None = None
    """Sent by Discord, but not documented; the older name of ``primary_guild``."""
    vad_colors: object | None = None
    """Sent by Discord, but not documented; always null so far."""


class Presence(DiscordModel):
    """https://docs.discord.com/developers/events/gateway-events#presence-update-presence-update-event-fields.

    ``guild_id`` is left out of the presences inside GUILD_CREATE and GUILD_MEMBERS_CHUNK.
    """

    user: PresenceUser
    guild_id: Snowflake | None = None
    status: Status
    activities: list[Activity]
    client_status: ClientStatus
    processed_at_timestamp: int | None = None
    """When Discord processed the update, as Unix milliseconds; ``0`` when it doesn't say. Sent by Discord, but not documented."""
