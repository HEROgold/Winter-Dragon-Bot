"""Presences (https://docs.discord.com/developers/events/gateway-events#presence-update)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.member import PartialMember
lazy from wd_discord.entities.user import PartialUser
lazy from wd_discord.gateway.presence import Presence as PresenceModel


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.gateway.presence import Activity, ClientStatus, Status


class Presence(Entity[PresenceModel]):
    """What a member is doing: whether they're online, and their activities."""

    @property
    def user(self) -> PartialUser:
        """The user the presence is for; Discord sends only part of them along."""
        return PartialUser(self.client, self.model.user.id)

    @property
    def guild(self) -> PartialGuild | None:
        """The guild the presence was seen in; ``None`` inside GUILD_CREATE and GUILD_MEMBERS_CHUNK."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def member(self) -> PartialMember | None:
        """The member the presence is for, when the guild is known."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialMember(self.client, self.model.user.id, guild_id)

    @property
    def status(self) -> Status:
        """Whether they're online, idle, on do-not-disturb or offline."""
        return self.model.status

    @property
    def activities(self) -> Generator[Activity]:
        """What they're doing, their custom status included."""
        yield from self.model.activities

    @property
    def client_status(self) -> ClientStatus:
        """Their status on each platform they're on."""
        return self.model.client_status
