"""Work out what a member may do in a guild or one of its channels, the way Discord does.

Follows https://docs.discord.com/developers/topics/permissions#permission-overwrites: the guild's owner may do
everything; otherwise the ``@everyone`` role and the member's roles add up, ADMINISTRATOR grants everything, and a
channel's overwrites apply in order: ``@everyone``, then the member's roles together, then the member.
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.channel import OverwriteType


if TYPE_CHECKING:
    from collections.abc import Iterable

    from wd_discord.resources.channel import Channel, PermissionOverwrite
    from wd_discord.resources.guild import Guild, GuildMember
    from wd_discord.snowflake import Snowflake


@dataclass(frozen=True)
class PermissionSolver:
    """The permissions ``member`` holds in ``guild``, and in each of its channels.

    ``guild`` must carry its roles, as ``GET /guilds/{guild_id}`` returns it; ``member`` must carry its user, as
    ``GET /guilds/{guild_id}/members/{user_id}`` returns it.
    """

    guild: Guild
    member: GuildMember

    @property
    def member_id(self) -> Snowflake:
        """The member's user ID."""
        if self.member.user is None:
            msg = "PermissionSolver needs a member with its user, as GET /guilds/{guild_id}/members/{user_id} returns it"
            raise ValueError(msg)
        return self.member.user.id

    def _has_role(self, role_id: Snowflake) -> bool:
        """Whether the member has the role ``role_id``; ``Snowflake`` is unhashable, hence the scan."""
        return any(role_id == own for own in self.member.roles)

    def base(self) -> Permissions:
        """Return the member's guild-wide permissions, before any channel overwrites."""
        if self.guild.owner_id == self.member_id:
            return Permissions.all()
        permissions = Permissions.none()
        for role in self.guild.roles:
            if role.id == self.guild.id or self._has_role(role.id):
                permissions |= role.permissions
        return Permissions.all() if Permissions.ADMINISTRATOR in permissions else permissions

    def in_channel(self, channel: Channel) -> Permissions:
        """Return the member's permissions in ``channel``: :meth:`base` with its overwrites applied."""
        permissions = self.base()
        if Permissions.ADMINISTRATOR in permissions:
            return permissions
        overwrites = channel.permission_overwrites or []
        everyone = [overwrite for overwrite in overwrites if overwrite.id == self.guild.id]
        roles = [
            overwrite
            for overwrite in overwrites
            if overwrite.type is OverwriteType.ROLE and overwrite.id != self.guild.id and self._has_role(overwrite.id)
        ]
        member = [
            overwrite for overwrite in overwrites if overwrite.type is OverwriteType.MEMBER and overwrite.id == self.member_id
        ]
        for layer in (everyone, roles, member):
            permissions = _apply(permissions, layer)
        return permissions


def _apply(permissions: Permissions, overwrites: Iterable[PermissionOverwrite]) -> Permissions:
    """Return ``permissions`` with every denial of ``overwrites`` removed, then every allowance of them added."""
    deny, allow = Permissions.none(), Permissions.none()
    for overwrite in overwrites:
        deny |= overwrite.deny
        allow |= overwrite.allow
    return (permissions & ~deny) | allow
