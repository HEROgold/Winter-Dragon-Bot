"""The objects a message carries besides its text: attachments, reactions and mentioned users."""

from __future__ import annotations

from wd_discord.models import DiscordModel
from wd_discord.partial_emoji import PartialEmoji
from wd_discord.resources.guild.member import GuildMember  # noqa: TC001 - pydantic resolves MentionedUser.member at runtime
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake


class Attachment(DiscordModel):
    """A file attached to a message (https://docs.discord.com/developers/resources/message#attachment-object)."""

    id: Snowflake
    filename: str
    title: str | None = None
    """The title of the file."""
    description: str | None = None
    """The file's description, up to 1024 characters."""
    content_type: str | None = None
    """The file's media type."""
    size: int
    """The file's size in bytes."""
    url: str
    """Where to download the file."""
    proxy_url: str
    """A proxied download URL."""
    height: int | None = None
    """The image's height, for images."""
    width: int | None = None
    """The image's width, for images."""
    placeholder: str | None = None
    """A thumbhash of the image, for images."""
    placeholder_version: int | None = None
    """The thumbhash's version."""
    ephemeral: bool | None = None
    """Whether the attachment is ephemeral."""
    duration_secs: float | None = None
    """The audio's length, for voice messages."""
    waveform: str | None = None
    """A base64 sampled waveform, for voice messages."""
    flags: int | None = None
    """Attachment flags, combined as a bitfield."""


class ReactionCountDetails(DiscordModel):
    """How a reaction count splits (https://docs.discord.com/developers/resources/message#reaction-count-details-object)."""

    burst: int
    """Super reactions."""
    normal: int
    """Normal reactions."""


class Reaction(DiscordModel):
    """One emoji's reactions on a message (https://docs.discord.com/developers/resources/message#reaction-object)."""

    count: int
    """Total times this emoji was used, super reactions included."""
    count_details: ReactionCountDetails
    me: bool
    """Whether the bot reacted with it."""
    me_burst: bool
    """Whether the bot super-reacted with it."""
    emoji: PartialEmoji
    burst_colors: list[str]
    """The super reaction's colors, as hex strings."""


class MentionedUser(User):
    """A user a message mentions; in a guild Discord adds their partial member (https://docs.discord.com/developers/resources/message#message-object)."""

    member: GuildMember | None = None
    """The user's membership of the message's guild, without its ``user``."""
