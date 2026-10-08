"""Guilds (https://docs.discord.com/developers/resources/guild)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content
lazy from wd_discord.entities.channel import Channel
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Guild as GuildModel


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.client import NetworkError
    from wd_discord.snowflake import Snowflake


class BaseGuild(ClientBound):
    """What can be done to a guild knowing only its ID: read it, list its channels, leave it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    async def fetch(self) -> Guild | NetworkError:
        """GET /guilds/{guild_id}."""
        return self._entity(await self.client.get(f"/guilds/{self.id}"), GuildModel, Guild)

    async def channels(self) -> Generator[Channel] | NetworkError:
        """GET /guilds/{guild_id}/channels - the guild's channels, threads excluded."""
        return self._entities(await self.client.get(f"/guilds/{self.id}/channels"), ChannelModel, Channel)

    async def leave(self) -> NetworkError | None:
        """DELETE /users/@me/guilds/{guild_id} - remove the bot from the guild; fails for a guild it owns."""
        return no_content(await self.client.delete(f"/users/@me/guilds/{self.id}", json={}))


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


class PartialGuild(BaseGuild, Partial[Guild]):
    """A guild known only by ID."""
