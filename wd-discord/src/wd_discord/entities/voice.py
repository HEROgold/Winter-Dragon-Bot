"""Voice states (https://docs.discord.com/developers/resources/voice#voice-state-object)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.resources.voice import VoiceState as VoiceStateModel


if TYPE_CHECKING:
    from wd_discord.snowflake import Snowflake


class VoiceState(Entity[VoiceStateModel]):
    """Which voice channel a user is in, bound to the client that can act on them and the channel."""

    @property
    def user_id(self) -> Snowflake:
        """The user this voice state is for."""
        return self.model.user_id

    @property
    def guild_id(self) -> Snowflake | None:
        """The guild this voice state is for; ``None`` for a voice state taken from GUILD_CREATE."""
        return self.model.guild_id

    @property
    def channel_id(self) -> Snowflake | None:
        """The voice channel the user is in; ``None`` once they disconnected."""
        return self.model.channel_id

    @property
    def channel(self) -> PartialChannel | None:
        """The voice channel the user is in; ``None`` once they disconnected."""
        channel_id = self.model.channel_id
        return None if channel_id is None else PartialChannel(self.client, channel_id)

    @property
    def member(self) -> Member | PartialMember | None:
        """The member this voice state is for, in full when Discord sent it; ``None`` outside a guild."""
        guild_id = self.model.guild_id
        if guild_id is None:
            return None
        if self.model.member is not None and self.model.member.user is not None:
            return Member(self.client, self.model.member, guild_id)
        return PartialMember(self.client, self.model.user_id, guild_id)
