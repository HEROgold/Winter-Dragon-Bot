"""Roles (https://docs.discord.com/developers/topics/permissions#role-object)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content, parse
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.resources.guild import Role as RoleModel


if TYPE_CHECKING:
    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError, RequestResult
    from wd_discord.image import ImageHash
    from wd_discord.permissions import Permissions
    from wd_discord.resources.guild.role import RoleColors, RoleTags
    from wd_discord.snowflake import Snowflake


class BaseRole(ClientBound):
    """What can be done to a role knowing only its guild and ID: read it, delete it, mention it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The role's ID."""

        @property
        def guild_id(self) -> Snowflake:
            """The guild the role belongs to."""

    @property
    def guild(self) -> PartialGuild:
        """The guild the role belongs to."""
        return PartialGuild(self.client, self.guild_id)

    @property
    def mention(self) -> str:
        """A clickable mention of the role, as ``<@&id>``; ``@everyone`` for the guild's default role."""
        return "@everyone" if self.is_default else f"<@&{self.id}>"

    @property
    def is_default(self) -> bool:
        """Whether this is the guild's ``@everyone`` role, which shares the guild's ID."""
        return self.id == self.guild_id

    async def fetch(self) -> Role | NetworkError:
        """GET /guilds/{guild_id}/roles/{role_id}."""
        return self._role(await self.client.get(t"/guilds/{self.guild_id}/roles/{self.id}"))

    async def delete(self, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /guilds/{guild_id}/roles/{role_id}; needs MANAGE_ROLES."""
        return no_content(await self.client.delete(t"/guilds/{self.guild_id}/roles/{self.id}", headers=reason_headers(reason)))

    def _role(self, result: RequestResult) -> Role | NetworkError:
        """Return the failure in ``result``, or its body as a :class:`Role` of this role's guild."""
        parsed = parse(result, RoleModel)
        return parsed if is_network_error(parsed) else Role(self.client, parsed, self.guild_id)


@dataclass(frozen=True)
class Role(Entity[RoleModel], BaseRole):
    """A role, as Discord returned it."""

    guild_id: Snowflake
    """The guild the role belongs to."""

    @property
    @override
    def id(self) -> Snowflake:
        """The role's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The role's name."""
        return self.model.name

    @property
    def color(self) -> int:
        """The role's color as an RGB integer; ``0`` for no color."""
        return self.model.color

    @property
    def colors(self) -> RoleColors | None:
        """The role's gradient colors, when it has them."""
        return self.model.colors

    @property
    def hoist(self) -> bool:
        """Whether members with this role show separately in the member list."""
        return self.model.hoist

    @property
    def icon(self) -> ImageHash | None:
        """The role's icon, if it has one."""
        return self.model.icon

    @property
    def unicode_emoji(self) -> str | None:
        """The role's unicode emoji, if it has one."""
        return self.model.unicode_emoji

    @property
    def position(self) -> int:
        """Where the role sits in the guild's role list; a higher role outranks a lower one."""
        return self.model.position

    @property
    def permissions(self) -> Permissions:
        """The permissions the role grants."""
        return self.model.permissions

    @property
    def managed(self) -> bool:
        """Whether an integration (a bot, boosting, a subscription) manages the role."""
        return self.model.managed

    @property
    def mentionable(self) -> bool:
        """Whether anyone may mention the role."""
        return self.model.mentionable

    @property
    def tags(self) -> RoleTags | None:
        """What manages the role, for a managed role."""
        return self.model.tags


@dataclass(frozen=True)
class PartialRole(BaseRole, Partial[Role]):
    """A role known only by guild and ID."""

    guild_id: Snowflake
    """The guild the role belongs to."""
