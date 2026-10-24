"""The current state of each Discord object the archive has seen.

Columns are a starting set, named after Discord's fields; every field without a column is kept as the row's
custom data, so adding a column later only moves that field out of it.
"""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field

from archive.models.base import ArchiveCompositeEntity, ArchiveEntity, moment, snowflake
from archive.models.children import (
    ChannelAppliedTag,
    EmojiRole,
    ForumTag,
    GuildFeature,
    MemberRole,
    MessageAttachment,
    MessageComponent,
    MessageEmbed,
    MessageMention,
    MessageMentionRole,
    MessagePoll,
    MessageReaction,
    MessageStickerItem,
    PermissionOverwrite,
)


class Guild(ArchiveEntity, table=True):
    """A guild (https://docs.discord.com/developers/resources/guild#guild-object)."""

    children: ClassVar = {"features": GuildFeature}

    name: str | None = None
    icon: str | None = None
    splash: str | None = None
    banner: str | None = None
    description: str | None = None
    owner_id: int | None = snowflake()
    afk_channel_id: int | None = snowflake()
    afk_timeout: int | None = None
    system_channel_id: int | None = snowflake()
    rules_channel_id: int | None = snowflake()
    verification_level: int | None = None
    default_message_notifications: int | None = None
    explicit_content_filter: int | None = None
    mfa_level: int | None = None
    nsfw_level: int | None = None
    premium_tier: int | None = None
    premium_subscription_count: int | None = None
    preferred_locale: str | None = None
    vanity_url_code: str | None = None
    max_members: int | None = None
    member_count: int | None = None
    large: bool | None = None
    unavailable: bool | None = None
    joined_at: datetime | None = moment()


class Channel(ArchiveEntity, table=True):
    """A channel or thread (https://docs.discord.com/developers/resources/channel#channel-object)."""

    children: ClassVar = {
        "permission_overwrites": PermissionOverwrite,
        "available_tags": ForumTag,
        "applied_tags": ChannelAppliedTag,
    }

    type: int | None = None
    guild_id: int | None = snowflake(index=True)
    parent_id: int | None = snowflake()
    owner_id: int | None = snowflake()
    name: str | None = None
    topic: str | None = None
    position: int | None = None
    nsfw: bool | None = None
    flags: int | None = None
    last_message_id: int | None = snowflake()
    last_pin_timestamp: datetime | None = moment()
    rate_limit_per_user: int | None = None
    bitrate: int | None = None
    user_limit: int | None = None
    rtc_region: str | None = None
    video_quality_mode: int | None = None
    status: str | None = None
    """A voice channel's status text."""
    voice_start_time: int | None = Field(default=None, sa_type=BigInteger)
    """When the current voice session in the channel started, in Unix seconds."""
    default_auto_archive_duration: int | None = None
    message_count: int | None = None
    member_count: int | None = None
    total_message_sent: int | None = None
    thread_metadata_archived: bool | None = None
    thread_metadata_locked: bool | None = None
    thread_metadata_auto_archive_duration: int | None = None
    thread_metadata_archive_timestamp: datetime | None = moment()
    thread_metadata_create_timestamp: datetime | None = moment()


class Role(ArchiveEntity, table=True):
    """A guild's role (https://docs.discord.com/developers/topics/permissions#role-object)."""

    guild_id: int | None = snowflake(index=True)
    name: str | None = None
    color: int | None = None
    colors_primary_color: int | None = None
    colors_secondary_color: int | None = None
    colors_tertiary_color: int | None = None
    hoist: bool | None = None
    icon: str | None = None
    unicode_emoji: str | None = None
    position: int | None = None
    permissions: str | None = None
    """The permission bit set, as Discord's decimal string: it outgrows a 64-bit integer."""
    managed: bool | None = None
    mentionable: bool | None = None
    flags: int | None = None
    tags_bot_id: int | None = snowflake()
    tags_integration_id: int | None = snowflake()


class User(ArchiveEntity, table=True):
    """A user (https://docs.discord.com/developers/resources/user#user-object)."""

    username: str | None = None
    discriminator: str | None = None
    global_name: str | None = None
    avatar: str | None = None
    banner: str | None = None
    accent_color: int | None = None
    bot: bool | None = None
    system: bool | None = None
    public_flags: int | None = None


class Member(ArchiveCompositeEntity, table=True):
    """A user's membership of a guild (https://docs.discord.com/developers/resources/guild#guild-member-object)."""

    natural_key: ClassVar = ("guild_id", "user_id")
    children: ClassVar = {"roles": MemberRole}

    guild_id: int = Field(sa_type=BigInteger)
    user_id: int = Field(sa_type=BigInteger, index=True)
    nick: str | None = None
    avatar: str | None = None
    banner: str | None = None
    joined_at: datetime | None = moment()
    premium_since: datetime | None = moment()
    communication_disabled_until: datetime | None = moment()
    deaf: bool | None = None
    mute: bool | None = None
    pending: bool | None = None
    flags: int | None = None


class ThreadMember(ArchiveCompositeEntity, table=True):
    """A user's membership of a thread (https://docs.discord.com/developers/resources/channel#thread-member-object)."""

    natural_key: ClassVar = ("thread_id", "user_id")
    renames: ClassVar = {"id": "thread_id"}

    thread_id: int = Field(sa_type=BigInteger)
    user_id: int = Field(sa_type=BigInteger, index=True)
    join_timestamp: datetime | None = moment()
    flags: int | None = None


class Emoji(ArchiveEntity, table=True):
    """A guild's custom emoji (https://docs.discord.com/developers/resources/emoji#emoji-object)."""

    children: ClassVar = {"roles": EmojiRole}

    guild_id: int | None = snowflake(index=True)
    name: str | None = None
    user_id: int | None = snowflake()
    """Who uploaded it."""
    require_colons: bool | None = None
    managed: bool | None = None
    animated: bool | None = None
    available: bool | None = None


class Sticker(ArchiveEntity, table=True):
    """A sticker (https://docs.discord.com/developers/resources/sticker#sticker-object)."""

    guild_id: int | None = snowflake(index=True)
    pack_id: int | None = snowflake()
    name: str | None = None
    description: str | None = None
    tags: str | None = None
    type: int | None = None
    format_type: int | None = None
    available: bool | None = None
    user_id: int | None = snowflake()
    sort_value: int | None = None


class Message(ArchiveEntity, table=True):
    """A message, with its content (https://docs.discord.com/developers/resources/message#message-object)."""

    children: ClassVar = {
        "attachments": MessageAttachment,
        "embeds": MessageEmbed,
        "components": MessageComponent,
        "mentions": MessageMention,
        "mention_roles": MessageMentionRole,
        "reactions": MessageReaction,
        "sticker_items": MessageStickerItem,
        "poll": MessagePoll,
    }

    channel_id: int | None = snowflake(index=True)
    guild_id: int | None = snowflake(index=True)
    author_id: int | None = snowflake(index=True)
    content: str | None = None
    timestamp: datetime | None = moment()
    edited_timestamp: datetime | None = moment()
    type: int | None = None
    flags: int | None = None
    tts: bool | None = None
    mention_everyone: bool | None = None
    pinned: bool | None = None
    webhook_id: int | None = snowflake()
    application_id: int | None = snowflake()
    position: int | None = None
    message_reference_type: int | None = None
    message_reference_message_id: int | None = snowflake()
    message_reference_channel_id: int | None = snowflake()
    message_reference_guild_id: int | None = snowflake()
