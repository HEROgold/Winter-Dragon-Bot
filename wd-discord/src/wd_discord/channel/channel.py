"""The Discord Channel object model."""
from __future__ import annotations

from datetime import datetime

from wd_discord.channel.forum import DefaultReaction, ForumLayoutType, ForumTag, SortOrderType, VideoQualityMode
from wd_discord.channel.overwrite import PermissionOverwrite
from wd_discord.channel.thread import ThreadMember, ThreadMetadata
from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.permissions import ChannelType, PermissionsField
from wd_discord.snowflake import Snowflake
from wd_discord.user import User


class Channel(DiscordModel):
    """https://docs.discord.com/developers/resources/channel#channel-object.

    Represents the union across every channel type; only ``id`` and ``type`` are effectively
    always present, so every other field defaults to ``None``.
    """

    id: Snowflake
    """The id of this channel."""
    type: ChannelType
    """The type of channel."""
    guild_id: Snowflake | None = None
    """The id of the guild (may be missing for some channel objects received over gateway guild dispatches)."""
    position: int | None = None
    """Sorting position of the channel."""
    permission_overwrites: list[PermissionOverwrite] | None = None
    """Explicit permission overwrites for members and roles."""
    name: str | None = None
    """The name of the channel."""
    topic: str | None = None
    """The channel topic."""
    nsfw: bool | None = None
    """Whether the channel is nsfw."""
    last_message_id: Snowflake | None = None
    """The id of the last message sent in this channel (or thread for forum/media channels)."""
    bitrate: int | None = None
    """The bitrate (in bits) of the voice channel."""
    user_limit: int | None = None
    """The user limit of the voice channel."""
    rate_limit_per_user: int | None = None
    """Amount of seconds a user has to wait before sending another message."""
    recipients: list[User] | None = None
    """The recipients of the DM."""
    icon: ImageHash | None = None
    """Icon hash of the group DM."""
    owner_id: Snowflake | None = None
    """Id of the creator of the group DM or thread."""
    application_id: Snowflake | None = None
    """Application id of the group DM creator if it is bot-created."""
    managed: bool | None = None
    """For group DM channels: whether the channel is managed by an application via the gdm.join OAuth2 scope."""
    parent_id: Snowflake | None = None
    """For guild channels: id of the parent category; for threads: id of the text channel this thread was created in."""
    last_pin_timestamp: datetime | None = None
    """When the last pinned message was pinned."""
    rtc_region: str | None = None
    """Voice region id for the voice channel, automatic when set to null."""
    video_quality_mode: VideoQualityMode | None = None
    """The camera video quality mode of the voice channel, 1 when not present."""
    message_count: int | None = None
    """Number of messages (not including the initial message or deleted messages) in a thread."""
    member_count: int | None = None
    """An approximate count of users in a thread, stops counting at 50."""
    thread_metadata: ThreadMetadata | None = None
    """Thread-specific fields not needed by other channels."""
    member: ThreadMember | None = None
    """Thread member object for the current user, if they have joined the thread."""
    default_auto_archive_duration: int | None = None
    """Default duration for newly created threads, in minutes, to automatically archive after recent activity."""
    permissions: PermissionsField | None = None
    """Computed permissions for the invoking user in the channel, including overwrites."""
    flags: int | None = None
    """Channel flags combined as a bitfield."""
    total_message_sent: int | None = None
    """Number of messages ever sent in a thread, does not decrement when a message is deleted."""
    available_tags: list[ForumTag] | None = None
    """The set of tags that can be used in a forum or media channel."""
    applied_tags: list[Snowflake] | None = None
    """The ids of the set of tags applied to a thread in a forum or media channel."""
    default_reaction_emoji: DefaultReaction | None = None
    """The emoji shown in the add reaction button on a thread in a forum or media channel."""
    default_thread_rate_limit_per_user: int | None = None
    """The initial rate_limit_per_user to set on newly created threads in a channel."""
    default_sort_order: SortOrderType | None = None
    """The default sort order used to order posts in a forum or media channel."""
    default_forum_layout: ForumLayoutType | None = None
    """The default forum layout view used to display posts in a forum channel."""
