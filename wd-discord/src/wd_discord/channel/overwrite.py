"""Permission overwrite models for the Discord Channel object."""
from __future__ import annotations

from enum import IntEnum

from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.snowflake import Snowflake


class OverwriteType(IntEnum):
    """Whether a permission overwrite targets a role or a member."""

    ROLE = 0
    """The overwrite applies to a role."""
    MEMBER = 1
    """The overwrite applies to a member."""


class PermissionOverwrite(DiscordModel):
    """https://docs.discord.com/developers/resources/channel#overwrite-object."""

    id: Snowflake
    """Role or user id."""
    type: OverwriteType
    """Whether this overwrite targets a role or a member."""
    allow: PermissionsField
    """Permission bit set that is explicitly allowed."""
    deny: PermissionsField
    """Permission bit set that is explicitly denied."""
