"""Voice states (https://docs.discord.com/developers/resources/voice#voice-state-object)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.entities.user import PartialUser, User
lazy from wd_discord.resources.voice import VoiceState as VoiceStateModel


if TYPE_CHECKING:
    from datetime import datetime


class VoiceState(Entity[VoiceStateModel]):
    """Which voice channel a user is in, and how they're muted, bound to the client that can act on them."""

    @property
    def user(self) -> User | PartialUser:
        """The user this voice state is for; in full when Discord sent their member along."""
        member = self.model.member
        if member is not None and member.user is not None:
            return User(self.client, member.user)
        return PartialUser(self.client, self.model.user_id)

    @property
    def member(self) -> Member | PartialMember | None:
        """The member this voice state is for, in full when Discord sent it; ``None`` outside a guild."""
        guild_id = self.model.guild_id
        if guild_id is None:
            return None
        if self.model.member is not None and self.model.member.user is not None:
            return Member(self.client, self.model.member, guild_id)
        return PartialMember(self.client, self.model.user_id, guild_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The guild this voice state is for; ``None`` outside a guild."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def channel(self) -> PartialChannel | None:
        """The voice channel the user is in; ``None`` once they disconnected."""
        channel_id = self.model.channel_id
        return None if channel_id is None else PartialChannel(self.client, channel_id)

    @property
    def session_id(self) -> str:
        """The voice session's ID."""
        return self.model.session_id

    @property
    def deaf(self) -> bool:
        """Whether the guild deafened the user."""
        return self.model.deaf

    @property
    def mute(self) -> bool:
        """Whether the guild muted the user."""
        return self.model.mute

    @property
    def self_deaf(self) -> bool:
        """Whether the user deafened themselves."""
        return self.model.self_deaf

    @property
    def self_mute(self) -> bool:
        """Whether the user muted themselves."""
        return self.model.self_mute

    @property
    def self_stream(self) -> bool:
        """Whether the user is streaming with Go Live."""
        return bool(self.model.self_stream)

    @property
    def self_video(self) -> bool:
        """Whether the user's camera is on."""
        return self.model.self_video

    @property
    def suppress(self) -> bool:
        """Whether the user may not speak, as in a stage channel's audience."""
        return self.model.suppress

    @property
    def request_to_speak_timestamp(self) -> datetime | None:
        """When the user raised their hand in a stage channel."""
        return self.model.request_to_speak_timestamp
