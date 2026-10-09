"""Request bodies for creating and modifying guild channels.

https://docs.discord.com/developers/resources/guild#create-guild-channel and
https://docs.discord.com/developers/resources/channel#modify-channel.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer
lazy from wd_core.client import ChannelPayload, OverwritePayload

from wd_discord.permissions import ChannelType, Permissions
from wd_discord.resources.channel.overwrite import OverwriteType
from wd_discord.snowflake import Snowflake


MAX_USER_LIMIT = 99
"""The most users a voice channel can be limited to; 0 means no limit."""

type ChannelName = Annotated[str, Field(min_length=1, max_length=100)]


class OverwriteParams(BaseModel):
    """One permission overwrite to set on a channel: what a role or member is explicitly allowed and denied.

    https://docs.discord.com/developers/resources/channel#overwrite-object.
    """

    model_config = ConfigDict(extra="forbid")

    id: Snowflake
    """The role or user the overwrite applies to."""
    type: OverwriteType
    """Whether :attr:`id` is a role or a member."""
    allow: Permissions = Permissions(0)
    """Permissions explicitly allowed."""
    deny: Permissions = Permissions(0)
    """Permissions explicitly denied."""

    @field_serializer("allow", "deny")
    def _bitfield(self, value: Permissions) -> str:
        """Discord takes permission bitfields as decimal strings."""
        return str(int(value))

    def to_json(self) -> OverwritePayload:
        """Return the overwrite as Discord's JSON body."""
        return OverwritePayload(**self.model_dump(mode="json"))


class _ChannelSettings(BaseModel):
    """The settings a channel is created with or changed to; only the fields set are sent."""

    model_config = ConfigDict(extra="forbid")

    topic: Annotated[str, Field(max_length=1024)] | None = None
    """The text channel's topic."""
    position: int | None = None
    """Sorting position among the guild's channels."""
    bitrate: Annotated[int, Field(ge=8000)] | None = None
    """The voice channel's bitrate, in bits."""
    user_limit: Annotated[int, Field(ge=0, le=MAX_USER_LIMIT)] | None = None
    """How many users fit in the voice channel; 0 means no limit."""
    rate_limit_per_user: Annotated[int, Field(ge=0, le=21600)] | None = None
    """Slowmode: seconds a user waits between messages."""
    nsfw: bool | None = None
    parent_id: Snowflake | None = None
    """The category the channel sits in."""
    permission_overwrites: list[OverwriteParams] | None = None
    """Replaces every overwrite on the channel."""

    def to_json(self) -> ChannelPayload:
        """Return the request body: only the fields set."""
        return ChannelPayload(**self.model_dump(mode="json", exclude_none=True))


class ChannelParams(_ChannelSettings):
    """The channel settings to change; the rest stay as they are."""

    name: ChannelName | None = None


class GuildChannelParams(_ChannelSettings):
    """A new guild channel or category; Discord requires its name."""

    name: ChannelName
    type: ChannelType = ChannelType.GUILD_TEXT
    """The kind of channel to create."""
