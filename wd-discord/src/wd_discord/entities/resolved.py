"""The objects an interaction's options name, as Discord sent them along.

https://docs.discord.com/developers/interactions/receiving-and-responding#interaction-object-resolved-data-structure
"""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import Channel
lazy from wd_discord.entities.role import Role
lazy from wd_discord.entities.user import User
lazy from wd_discord.gateway.events import ResolvedData
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from wd_discord.snowflake import SnowflakeLike


@dataclass(frozen=True)
class Resolved(Entity[ResolvedData]):
    """Full objects for the user, role and channel IDs an interaction's option values hold, keyed by ID."""

    guild_id: Snowflake | None
    """The guild the interaction was sent from, which the roles belong to."""

    @property
    def users(self) -> dict[Snowflake, User]:
        """The users option values name."""
        return {Snowflake.coerce(key): User(self.client, user) for key, user in (self.model.users or {}).items()}

    @property
    def roles(self) -> dict[Snowflake, Role]:
        """The roles option values name; empty outside a guild."""
        guild_id = self.guild_id
        if guild_id is None:
            return {}
        return {Snowflake.coerce(key): Role(self.client, role, guild_id) for key, role in (self.model.roles or {}).items()}

    @property
    def channels(self) -> dict[Snowflake, Channel]:
        """The channels option values name, with the invoking user's ``permissions`` in each.

        Discord sends only part of each channel: ``id``, ``name``, ``type``, ``permissions`` and, for threads,
        ``parent_id`` and ``thread_metadata``.
        """
        channels = self.model.channels or {}
        return {Snowflake.coerce(key): Channel(self.client, channel) for key, channel in channels.items()}

    def user(self, user_id: SnowflakeLike) -> User | None:
        """Return the user ``user_id`` names, if Discord sent them along."""
        return self.users.get(Snowflake.coerce(user_id))

    def role(self, role_id: SnowflakeLike) -> Role | None:
        """Return the role ``role_id`` names, if Discord sent it along."""
        return self.roles.get(Snowflake.coerce(role_id))

    def channel(self, channel_id: SnowflakeLike) -> Channel | None:
        """Return the channel ``channel_id`` names, if Discord sent it along."""
        return self.channels.get(Snowflake.coerce(channel_id))
