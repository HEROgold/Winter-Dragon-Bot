"""Discord role models (role, role tags, and role colors)."""

from typing import Annotated

from pydantic import Field

from wd_discord.color import Color
from wd_discord.image import ImageHash
from wd_discord.models import DiscordModel
from wd_discord.permissions import PermissionsField
from wd_discord.snowflake import Snowflake


class RoleTags(DiscordModel):
    """https://docs.discord.com/developers/topics/permissions#role-object-role-tags-structure."""

    bot_id: Snowflake | None = None
    """The id of the bot this role belongs to."""
    integration_id: Snowflake | None = None
    """The id of the integration this role belongs to."""
    premium_subscriber: bool | None = None
    """Whether this is the guild's Booster role."""
    subscription_listing_id: Snowflake | None = None
    """The id of this role's subscription sku and listing."""
    available_for_purchase: bool | None = None
    """Whether this role is available for purchase."""
    guild_connections: bool | None = None
    """Whether this role is a guild's linked role."""


class RoleColors(DiscordModel):
    """https://docs.discord.com/developers/topics/permissions#role-object-role-colors-object."""

    primary_color: Color
    """The primary color for the role."""
    secondary_color: Color | None
    """The secondary color for the role, making the role a gradient."""
    tertiary_color: Color | None
    """The tertiary color for the role, making the role a holographic style."""


class Role(DiscordModel):
    """https://docs.discord.com/developers/topics/permissions#role-object."""

    id: Snowflake
    """Role id."""
    name: str
    """Role name."""
    color: Color
    """Integer representation of hexadecimal color code."""
    colors: RoleColors | None = None
    """The role's colors."""
    hoist: bool
    """Whether this role is pinned in the user listing."""
    icon: ImageHash | None = None
    """Role icon hash."""
    unicode_emoji: str | None = None
    """Role unicode emoji."""
    position: Annotated[int, Field(ge=0)]
    """Position of this role (roles with the same position are sorted by id)."""
    permissions: PermissionsField
    """Permission bit set."""
    managed: bool
    """Whether this role is managed by an integration."""
    mentionable: bool
    """Whether this role is mentionable."""
    tags: RoleTags | None = None
    """The tags this role has."""
    flags: int
    """Role flags combined as a bitfield."""
