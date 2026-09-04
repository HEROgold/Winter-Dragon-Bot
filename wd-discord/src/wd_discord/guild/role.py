"""Discord role models (role, role tags, and role colors)."""

from __future__ import annotations

lazy from wd_discord.image import ImageHash
lazy from wd_discord.models import DiscordModel
lazy from wd_discord.permissions import PermissionsField
lazy from wd_discord.snowflake import Snowflake


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

    primary_color: int # TODO: Make a Color type, int is a primitive we don't want.
    """The primary color for the role."""
    secondary_color: int | None
    """The secondary color for the role, making the role a gradient."""
    tertiary_color: int | None
    """The tertiary color for the role, making the role a holographic style."""


class Role(DiscordModel):
    """https://docs.discord.com/developers/topics/permissions#role-object."""

    id: Snowflake
    """Role id."""
    name: str
    """Role name."""
    color: int
    """Integer representation of hexadecimal color code."""
    colors: RoleColors | None = None
    """The role's colors."""
    hoist: bool
    """Whether this role is pinned in the user listing."""
    icon: ImageHash | None = None
    """Role icon hash."""
    unicode_emoji: str | None = None
    """Role unicode emoji."""
    position: int # TODO: Perhaps we want a decorator here, or use pydantic to limit this. Discord's api might be able to tell us what it's max value is, but we don't know it yet.
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
