"""The lists inside archived payloads, one table per kind of list item.

Each row carries ``owner_id``, ``parent_id`` and ``position`` (see :class:`~archive.models.base.ArchiveChild`).
A list of plain values (role IDs, labels) stores each value in the table's :attr:`~ArchiveChild.scalar` column.
"""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field

from archive.models.base import ArchiveChild, moment, snowflake


# Guilds, channels, members and emojis.


class GuildFeature(ArchiveChild, table=True):
    """One of a guild's feature flags, such as ``COMMUNITY``."""

    scalar: ClassVar = "feature"

    feature: str


class PermissionOverwrite(ArchiveChild, table=True):
    """A role's or member's permission overwrite on a channel."""

    renames: ClassVar = {"id": "target_id"}

    target_id: int | None = snowflake()
    type: int | None = None
    """0 for a role, 1 for a member."""
    allow: str | None = None
    deny: str | None = None


class ForumTag(ArchiveChild, table=True):
    """A tag a forum channel offers its posts."""

    discord_id: int | None = snowflake()
    name: str | None = None
    moderated: bool | None = None
    emoji_id: int | None = snowflake()
    emoji_name: str | None = None


class ChannelAppliedTag(ArchiveChild, table=True):
    """A forum tag applied to a forum post."""

    scalar: ClassVar = "tag_id"

    tag_id: int = Field(sa_type=BigInteger)


class MemberRole(ArchiveChild, table=True):
    """A role a member has."""

    scalar: ClassVar = "role_id"

    role_id: int = Field(sa_type=BigInteger, index=True)


class EmojiRole(ArchiveChild, table=True):
    """A role allowed to use an emoji."""

    scalar: ClassVar = "role_id"

    role_id: int = Field(sa_type=BigInteger)


# Messages.


class MessageAttachment(ArchiveChild, table=True):
    """A file attached to a message."""

    discord_id: int | None = snowflake()
    filename: str | None = None
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    size: int | None = Field(default=None, sa_type=BigInteger)
    url: str | None = None
    proxy_url: str | None = None
    height: int | None = None
    width: int | None = None
    duration_secs: float | None = None
    flags: int | None = None


class MessageEmbedField(ArchiveChild, table=True):
    """One name/value field of an embed."""

    name: str | None = None
    value: str | None = None
    inline: bool | None = None


class MessageEmbed(ArchiveChild, table=True):
    """An embed in a message."""

    children: ClassVar = {"fields": MessageEmbedField}

    type: str | None = None
    title: str | None = None
    description: str | None = None
    url: str | None = None
    timestamp: datetime | None = moment()
    color: int | None = None
    author_name: str | None = None
    author_url: str | None = None
    author_icon_url: str | None = None
    footer_text: str | None = None
    footer_icon_url: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    video_url: str | None = None
    provider_name: str | None = None
    provider_url: str | None = None


class MessageSelectOption(ArchiveChild, table=True):
    """An option of a select menu component."""

    label: str | None = None
    value: str | None = None
    description: str | None = None
    default: bool | None = None
    emoji_id: int | None = snowflake()
    emoji_name: str | None = None


class MessageComponent(ArchiveChild, table=True):
    """A component in a message; components inside it (an action row's buttons) are its children."""

    type: int | None = None
    discord_id: int | None = None
    """The component's own numeric id within the message, not a Discord ID."""
    custom_id: str | None = None
    style: int | None = None
    label: str | None = None
    url: str | None = None
    disabled: bool | None = None
    placeholder: str | None = None
    min_values: int | None = None
    max_values: int | None = None
    content: str | None = None
    """A text display component's text."""
    emoji_id: int | None = snowflake()
    emoji_name: str | None = None


MessageComponent.children = {"components": MessageComponent, "options": MessageSelectOption}


class MessageMention(ArchiveChild, table=True):
    """A user a message mentions."""

    renames: ClassVar = {"id": "user_id"}

    user_id: int | None = snowflake(index=True)
    username: str | None = None


class MessageMentionRole(ArchiveChild, table=True):
    """A role a message mentions."""

    scalar: ClassVar = "role_id"

    role_id: int = Field(sa_type=BigInteger)


class MessageReaction(ArchiveChild, table=True):
    """One emoji's reaction count on a message, as the message last carried it."""

    renames: ClassVar = {"count": "reaction_count"}

    reaction_count: int | None = None
    """Discord's ``count``, renamed: ``count`` is a herogold model method."""
    count_details_normal: int | None = None
    count_details_burst: int | None = None
    me: bool | None = None
    me_burst: bool | None = None
    emoji_id: int | None = snowflake()
    emoji_name: str | None = None
    emoji_animated: bool | None = None


class MessageStickerItem(ArchiveChild, table=True):
    """A sticker sent in a message."""

    renames: ClassVar = {"id": "sticker_id"}

    sticker_id: int | None = snowflake()
    name: str | None = None
    format_type: int | None = None


class MessagePollAnswer(ArchiveChild, table=True):
    """One answer of a poll."""

    answer_id: int | None = None
    poll_media_text: str | None = None


class MessagePoll(ArchiveChild, table=True):
    """A message's poll; a message has at most one, stored as a one-item list."""

    children: ClassVar = {"answers": MessagePollAnswer}

    question_text: str | None = None
    expiry: datetime | None = moment()
    allow_multiselect: bool | None = None
    layout_type: int | None = None


# Presences.


class ActivityButton(ArchiveChild, table=True):
    """The label of a button an activity shows."""

    scalar: ClassVar = "label"

    label: str


class Activity(ArchiveChild, table=True):
    """One activity in a presence: a game, listening, streaming, a custom status."""

    renames: ClassVar = {"id": "discord_id", "created_at": "activity_created_at"}
    children: ClassVar = {"buttons": ActivityButton}

    discord_id: str | None = None
    type: int | None = None
    name: str | None = None
    url: str | None = None
    details: str | None = None
    state: str | None = None
    application_id: int | None = snowflake(index=True)
    activity_created_at: int | None = Field(default=None, sa_type=BigInteger)
    """When the activity was added to the user's session, in Unix milliseconds."""
    timestamps_start: int | None = Field(default=None, sa_type=BigInteger)
    timestamps_end: int | None = Field(default=None, sa_type=BigInteger)
    sync_id: str | None = None
    """For Spotify, the track ID."""
    session_id: str | None = None
    platform: str | None = None
    flags: int | None = None
    status_display_type: int | None = None
    emoji_id: int | None = snowflake()
    emoji_name: str | None = None
    emoji_animated: bool | None = None
    party_id: str | None = None
    assets_large_image: str | None = None
    assets_large_text: str | None = None
    assets_small_image: str | None = None
    assets_small_text: str | None = None
