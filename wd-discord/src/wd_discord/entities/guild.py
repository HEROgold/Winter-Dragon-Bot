"""Guilds (https://docs.discord.com/developers/resources/guild)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content
lazy from wd_discord.entities.channel import Channel
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Guild as GuildModel
lazy from wd_discord.resources.guild import GuildMember
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError
    from wd_discord.resources.channel import GuildChannelParams
    from wd_discord.snowflake import SnowflakeLike


MAX_MEMBERS_PER_PAGE = 1000
"""The most members ``GET /guilds/{guild_id}/members`` returns at once."""


class BaseGuild(ClientBound):
    """What can be done to a guild knowing only its ID: read it, list and create its channels, list its members."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    async def fetch(self, *, with_counts: bool = False) -> Guild | NetworkError:
        """GET /guilds/{guild_id}; ``with_counts`` fills in the approximate member and online counts."""
        params = {"with_counts": "true"} if with_counts else {}
        return self._entity(await self.client.get(t"/guilds/{self.id}", params=params), GuildModel, Guild)

    async def channels(self) -> Generator[Channel] | NetworkError:
        """GET /guilds/{guild_id}/channels - the guild's channels, threads excluded."""
        return self._entities(await self.client.get(t"/guilds/{self.id}/channels"), ChannelModel, Channel)

    async def create_channel(
        self,
        params: GuildChannelParams,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> Channel | NetworkError:
        """POST /guilds/{guild_id}/channels - create a channel or category; needs MANAGE_CHANNELS."""
        result = await self.client.post(t"/guilds/{self.id}/channels", json=params.to_json(), headers=reason_headers(reason))
        return self._entity(result, ChannelModel, Channel)

    def member(self, user_id: SnowflakeLike) -> PartialMember:
        """Return a handle on the member ``user_id`` of this guild, without fetching them."""
        return PartialMember(self.client, Snowflake.coerce(user_id), self.id)

    async def members(
        self,
        *,
        after: SnowflakeLike | None = None,
        limit: int = MAX_MEMBERS_PER_PAGE,
    ) -> Generator[Member] | NetworkError:
        """GET /guilds/{guild_id}/members - one page of members, by user ID, after the user ``after``.

        Pass the last member's ID as ``after`` to get the next page; a page shorter than ``limit`` is the last.
        Needs the GUILD_MEMBERS intent.
        """
        params = {"limit": str(limit), "after": str(after or 0)}
        result = await self.client.get(t"/guilds/{self.id}/members", params=params)
        if is_network_error(result):
            return result
        return (Member(self.client, GuildMember.model_validate(item), self.id) for item in result.json())

    async def leave(self) -> NetworkError | None:
        """DELETE /users/@me/guilds/{guild_id} - remove the bot from the guild; fails for a guild it owns."""
        return no_content(await self.client.delete(t"/users/@me/guilds/{self.id}", json={}))


class Guild(Entity[GuildModel], BaseGuild):
    """A guild, as Discord returned it."""

    @property
    @override
    def id(self) -> Snowflake:
        """The guild's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The guild's name."""
        return self.model.name

    @property
    def owner_id(self) -> Snowflake:
        """The ID of the guild's owner."""
        return self.model.owner_id

    @property
    def afk_channel_id(self) -> Snowflake | None:
        """The voice channel idle members are moved to, if the guild has one."""
        return self.model.afk_channel_id


class PartialGuild(BaseGuild, Partial[Guild]):
    """A guild known only by ID."""
