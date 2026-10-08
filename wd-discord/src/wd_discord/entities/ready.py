"""The READY a shard receives once it has connected (https://docs.discord.com/developers/events/gateway-events#ready)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.user import CurrentUser
lazy from wd_discord.gateway.events import Ready as ReadyModel


if TYPE_CHECKING:
    from collections.abc import Generator


class Ready(Entity[ReadyModel]):
    """A shard finished connecting: who the bot is, and which guilds will follow as GUILD_CREATE."""

    @property
    def user(self) -> CurrentUser:
        """The user behind the client's token."""
        return CurrentUser(self.client, self.model.user)

    @property
    def guilds(self) -> Generator[PartialGuild]:
        """The guilds this shard serves; each one arrives in full later as a GUILD_CREATE."""
        for guild in self.model.guilds:
            yield PartialGuild(self.client, guild.id)

    @property
    def session_id(self) -> str:
        """The session ID, for resuming the connection."""
        return self.model.session_id

    @property
    def shard(self) -> tuple[int, int] | None:
        """The ``(shard_id, num_shards)`` of the shard that received it, when sharding."""
        return self.model.shard

    @property
    def application_id(self) -> str | None:
        """The ID of the bot's application."""
        return self.model.application_id
