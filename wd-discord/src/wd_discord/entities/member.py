"""Guild members (https://docs.discord.com/developers/resources/guild#guild-member-object)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content, parse
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.role import PartialRole
lazy from wd_discord.entities.user import PartialUser, User
lazy from wd_discord.resources.guild import GuildMember


if TYPE_CHECKING:
    from collections.abc import Generator
    from datetime import datetime
    from string.templatelib import Template

    from wd_core.client import JsonPayload

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError, RequestResult
    from wd_discord.entities.channel import BaseChannel
    from wd_discord.entities.role import BaseRole
    from wd_discord.image import ImageHash
    from wd_discord.permissions import Permissions
    from wd_discord.resources.guild.member import GuildMemberFlags
    from wd_discord.snowflake import Snowflake


class BaseMember(ClientBound):
    """What can be done to a guild member knowing only their guild and user ID: read, edit, moderate them."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The member's user ID."""

        @property
        def guild_id(self) -> Snowflake:
            """The guild the member is in."""

    @property
    def mention(self) -> str:
        """A clickable mention of the member, as ``<@id>``."""
        return f"<@{self.id}>"

    @property
    def guild(self) -> PartialGuild:
        """The guild the member is in."""
        return PartialGuild(self.client, self.guild_id)

    @property
    def _path(self) -> Template:
        return t"/guilds/{self.guild_id}/members/{self.id}"

    async def fetch(self) -> Member | NetworkError:
        """GET /guilds/{guild_id}/members/{user_id}."""
        return self._member(await self.client.get(self._path))

    async def _edit(self, payload: JsonPayload, reason: AuditLogReason | str | None) -> Member | NetworkError:
        """PATCH /guilds/{guild_id}/members/{user_id} with ``payload``."""
        return self._member(await self.client.patch(self._path, json=payload, headers=reason_headers(reason)))

    async def move_to(
        self,
        channel: BaseChannel | None,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> Member | NetworkError:
        """PATCH /guilds/{guild_id}/members/{user_id} - move the member to the voice ``channel``.

        ``None`` disconnects them. Fails when the member isn't connected to voice; needs MOVE_MEMBERS, and CONNECT on
        the target channel.
        """
        return await self._edit({"channel_id": None if channel is None else str(channel.id)}, reason)

    async def set_nick(self, nick: str | None, *, reason: AuditLogReason | str | None = None) -> Member | NetworkError:
        """PATCH /guilds/{guild_id}/members/{user_id} - set the member's nickname, or clear it with ``None``.

        Needs MANAGE_NICKNAMES; the guild owner's nickname can't be changed by anyone else.
        """
        return await self._edit({"nick": nick}, reason)

    async def timeout(
        self,
        until: datetime | None,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> Member | NetworkError:
        """PATCH /guilds/{guild_id}/members/{user_id} - time the member out until ``until`` (at most 28 days ahead).

        ``None`` lifts the timeout. Needs MODERATE_MEMBERS.
        """
        return await self._edit({"communication_disabled_until": None if until is None else until.isoformat()}, reason)

    async def add_role(self, role: BaseRole, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """PUT /guilds/{guild_id}/members/{user_id}/roles/{role_id}; needs MANAGE_ROLES and a higher role."""
        return no_content(await self.client.put(self._path + t"/roles/{role.id}", json={}, headers=reason_headers(reason)))

    async def remove_role(self, role: BaseRole, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /guilds/{guild_id}/members/{user_id}/roles/{role_id}; needs MANAGE_ROLES and a higher role."""
        return no_content(await self.client.delete(self._path + t"/roles/{role.id}", headers=reason_headers(reason)))

    async def kick(self, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /guilds/{guild_id}/members/{user_id} - remove the member from the guild; needs KICK_MEMBERS."""
        return no_content(await self.client.delete(self._path, headers=reason_headers(reason)))

    async def ban(
        self,
        *,
        delete_message_seconds: int = 0,
        reason: AuditLogReason | str | None = None,
    ) -> NetworkError | None:
        """PUT /guilds/{guild_id}/bans/{user_id} - ban the member; needs BAN_MEMBERS.

        ``delete_message_seconds`` (at most 604800, 7 days) also deletes their messages from that long ago up to now.
        """
        payload: JsonPayload = {"delete_message_seconds": delete_message_seconds}
        route = t"/guilds/{self.guild_id}/bans/{self.id}"
        return no_content(await self.client.put(route, json=payload, headers=reason_headers(reason)))

    async def unban(self, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /guilds/{guild_id}/bans/{user_id} - lift the ban on this user; needs BAN_MEMBERS."""
        return no_content(await self.client.delete(t"/guilds/{self.guild_id}/bans/{self.id}", headers=reason_headers(reason)))

    def _member(self, result: RequestResult) -> Member | NetworkError:
        """Return the failure in ``result``, or its body as a :class:`Member` of this member's guild."""
        parsed = parse(result, GuildMember)
        return parsed if is_network_error(parsed) else Member(self.client, parsed, self.guild_id)


@dataclass(frozen=True)
class Member(Entity[GuildMember], BaseMember):
    """A guild member, as Discord returned them; always with their user."""

    guild_id: Snowflake
    """The guild the member is in."""

    @property
    @override
    def id(self) -> Snowflake:
        """The member's user ID."""
        return self.user.id

    @property
    def user(self) -> User:
        """The user behind the membership."""
        if self.model.user is None:
            msg = "This member was sent without its user"
            raise ValueError(msg)
        return User(self.client, self.model.user)

    @property
    def bot(self) -> bool:
        """Whether the member is a bot account."""
        return self.model.user is not None and bool(self.model.user.bot)

    @property
    def nick(self) -> str | None:
        """The member's guild nickname, if set."""
        return self.model.nick

    @property
    def display_name(self) -> str:
        """The member's guild nickname, else their global display name, else their username."""
        return self.model.nick or self.user.display_name

    @property
    def avatar(self) -> ImageHash | None:
        """The member's guild-specific avatar, if set."""
        return self.model.avatar

    @property
    def roles(self) -> Generator[PartialRole]:
        """The member's roles, ``@everyone`` excluded."""
        for role_id in self.model.roles:
            yield PartialRole(self.client, role_id, self.guild_id)

    @property
    def joined_at(self) -> datetime | None:
        """When the member joined the guild; ``None`` for a guest in a voice channel."""
        return self.model.joined_at

    @property
    def premium_since(self) -> datetime | None:
        """When the member started boosting the guild; ``None`` when not boosting."""
        return self.model.premium_since

    @property
    def deaf(self) -> bool:
        """Whether the member is deafened in voice channels."""
        return self.model.deaf

    @property
    def mute(self) -> bool:
        """Whether the member is muted in voice channels."""
        return self.model.mute

    @property
    def pending(self) -> bool:
        """Whether the member hasn't passed the guild's membership screening yet."""
        return bool(self.model.pending)

    @property
    def flags(self) -> GuildMemberFlags:
        """The member's guild member flags."""
        return self.model.flags

    @property
    def permissions(self) -> Permissions | None:
        """The member's permissions in the interaction's channel; only known for an interaction's member."""
        return self.model.permissions

    @property
    def communication_disabled_until(self) -> datetime | None:
        """When the member's timeout ends; ``None`` (or a past time) when not timed out."""
        return self.model.communication_disabled_until


@dataclass(frozen=True)
class PartialMember(BaseMember, Partial[Member]):
    """A guild member known only by guild and user ID."""

    guild_id: Snowflake
    """The guild the member is in."""

    @property
    def user(self) -> PartialUser:
        """The user behind the membership."""
        return PartialUser(self.client, self.id)
