"""Guilds (https://docs.discord.com/developers/resources/guild)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity, Store, no_content, parse
lazy from wd_discord.entities.channel import Channel
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Guild as GuildModel
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.client import Client, NetworkError
    from wd_discord.snowflake import SnowflakeLike


class BaseGuild(ABC):
    """What can be done to a guild knowing only its ID: read it, list its channels, leave it."""

    client: Client

    @property
    @abstractmethod
    def id(self) -> Snowflake:
        """The guild's ID."""

    async def fetch(self) -> Guild | NetworkError:
        """GET /guilds/{guild_id}."""
        guild = parse(await self.client.get(f"/guilds/{self.id}"), GuildModel)
        return guild if is_network_error(guild) else Guild(self.client, guild)

    async def channels(self) -> Generator[Channel] | NetworkError:
        """GET /guilds/{guild_id}/channels - the guild's channels, threads excluded."""
        result = await self.client.get(f"/guilds/{self.id}/channels")
        if is_network_error(result):
            return result
        return (Channel(self.client, ChannelModel.model_validate(channel)) for channel in result.json())

    async def leave(self) -> NetworkError | None:
        """DELETE /users/@me/guilds/{guild_id} - remove the bot from the guild; fails for a guild it owns."""
        return no_content(await self.client.delete(f"/users/@me/guilds/{self.id}", json={}))


@dataclass(frozen=True)
class PartialGuild(BaseGuild):
    """A guild known only by ID."""

    client: Client
    guild_id: Snowflake

    @property
    def id(self) -> Snowflake:
        """The guild's ID."""
        return self.guild_id


class Guild(Entity[GuildModel], BaseGuild):
    """A guild, as Discord returned it."""

    @property
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


@dataclass(frozen=True)
class GuildStore(Store):
    """Guilds the client is in."""

    def partial(self, guild_id: SnowflakeLike) -> PartialGuild:
        """Return a handle on the guild ``guild_id``, without fetching it."""
        return PartialGuild(self.client, Snowflake.coerce(guild_id))

    async def fetch(self, guild_id: SnowflakeLike) -> Guild | NetworkError:
        """GET /guilds/{guild_id}."""
        return await self.partial(guild_id).fetch()
