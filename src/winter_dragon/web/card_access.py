"""Who may open a channel's card: a member who could see that channel in Discord.

Discord computes permissions for a member in a channel from their roles and the channel's overwrites
(https://docs.discord.com/developers/topics/permissions#permission-overwrites). The card shows only what the viewer
could already see there, so it applies the same rules.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.channel import OverwriteType


if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from wd_discord.resources.channel import PermissionOverwrite
    from wd_discord.snowflake import Snowflake


@dataclass(frozen=True)
class GuildMember:
    """A member as a guild's permissions see them."""

    guild_id: Snowflake
    owner_id: Snowflake
    """The guild owner's user ID."""
    member_id: Snowflake
    member_roles: Collection[Snowflake]
    """The member's roles, ``@everyone`` left out as Discord sends it."""
    role_permissions: Mapping[Snowflake, Permissions]
    """The permissions of every role of the guild, ``@everyone`` (whose ID is the guild's) included."""


def can_view_channel(who: GuildMember, overwrites: Collection[PermissionOverwrite]) -> bool:
    """Return whether the member holds View Channel in a channel with these ``overwrites``, the way Discord works it out."""
    guild_id, member_id, member_roles, role_permissions = who.guild_id, who.member_id, who.member_roles, who.role_permissions
    owner_id = who.owner_id
    if member_id == owner_id:
        return True
    permissions = role_permissions.get(guild_id, Permissions(0))
    for role_id in member_roles:
        permissions |= role_permissions.get(role_id, Permissions(0))
    if Permissions.ADMINISTRATOR in permissions:
        return True
    by_id = {(overwrite.type, overwrite.id): overwrite for overwrite in overwrites}
    if (everyone := by_id.get((OverwriteType.ROLE, guild_id))) is not None:
        permissions = (permissions & ~everyone.deny) | everyone.allow
    denied = Permissions(0)
    allowed = Permissions(0)
    for role_id in member_roles:
        if (overwrite := by_id.get((OverwriteType.ROLE, role_id))) is not None:
            denied |= overwrite.deny
            allowed |= overwrite.allow
    permissions = (permissions & ~denied) | allowed
    if (own := by_id.get((OverwriteType.MEMBER, member_id))) is not None:
        permissions = (permissions & ~own.deny) | own.allow
    return Permissions.VIEW_CHANNEL in permissions
