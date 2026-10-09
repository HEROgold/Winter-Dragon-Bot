"""Guild members (https://docs.discord.com/developers/resources/guild#guild-member-object)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, parse
lazy from wd_discord.resources.guild import GuildMember


if TYPE_CHECKING:
    from wd_core.client import JsonPayload

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError, RequestResult
    from wd_discord.snowflake import Snowflake, SnowflakeLike


class BaseMember(ClientBound):
    """What can be done to a guild member knowing only their guild and user ID: read them, move them in voice."""

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

    async def fetch(self) -> Member | NetworkError:
        """GET /guilds/{guild_id}/members/{user_id}."""
        result = await self.client.get(t"/guilds/{self.guild_id}/members/{self.id}")
        return self._member(result)

    async def move_to(
        self,
        channel_id: SnowflakeLike | None,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> Member | NetworkError:
        """PATCH /guilds/{guild_id}/members/{user_id} - move the member to the voice channel ``channel_id``.

        ``None`` disconnects them. Fails when the member isn't connected to voice; needs MOVE_MEMBERS, and CONNECT on
        the target channel.
        """
        payload: JsonPayload = {"channel_id": None if channel_id is None else str(channel_id)}
        result = await self.client.patch(
            t"/guilds/{self.guild_id}/members/{self.id}",
            json=payload,
            headers=reason_headers(reason),
        )
        return self._member(result)

    def _member(self, result: RequestResult) -> Member | NetworkError:
        """Return the failure in ``result``, or its body as a :class:`Member` of this member's guild."""
        parsed = parse(result, GuildMember)
        return parsed if is_network_error(parsed) else Member(self.client, parsed, self.guild_id)


@dataclass(frozen=True)
class Member(Entity[GuildMember], BaseMember):
    """A guild member, as Discord returned them; always with their user."""

    guild: Snowflake
    """The guild the member is in."""

    @property
    @override
    def guild_id(self) -> Snowflake:
        """The guild the member is in."""
        return self.guild

    @property
    @override
    def id(self) -> Snowflake:
        """The member's user ID."""
        if self.model.user is None:
            msg = "This member was sent without its user"
            raise ValueError(msg)
        return self.model.user.id

    @property
    def bot(self) -> bool:
        """Whether the member is a bot account."""
        return self.model.user is not None and bool(self.model.user.bot)

    @property
    def display_name(self) -> str:
        """The member's guild nickname, else their global display name, else their username."""
        user = self.model.user
        if self.model.nick:
            return self.model.nick
        if user is None:
            return str(self.id)
        return user.global_name or user.username


@dataclass(frozen=True)
class PartialMember(BaseMember, Partial[Member]):
    """A guild member known only by guild and user ID."""

    guild: Snowflake
    """The guild the member is in."""

    @property
    @override
    def guild_id(self) -> Snowflake:
        """The guild the member is in."""
        return self.guild
