"""Gateway events that are about more than one entity, bound to the client that received them.

An event about one thing binds to that thing (CHANNEL_CREATE is a :class:`~wd_discord.entities.channel.Channel`).
The events here carry several, or facts besides the entity (GUILD_DELETE says whether the guild only went offline),
so each gets its own class exposing the entities as relations next to those facts.
"""

from __future__ import annotations

lazy from datetime import UTC, datetime
lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import Channel, PartialChannel, ThreadMember
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.gateway.events import ChannelPinsUpdate as ChannelPinsUpdateModel
lazy from wd_discord.gateway.events import GuildDelete as GuildDeleteModel
lazy from wd_discord.gateway.events import ThreadCreate as ThreadCreateModel
lazy from wd_discord.gateway.events import ThreadDelete as ThreadDeleteModel
lazy from wd_discord.gateway.events import ThreadListSync as ThreadListSyncModel
lazy from wd_discord.gateway.events import ThreadMembersUpdate as ThreadMembersUpdateModel
lazy from wd_discord.gateway.events import VoiceChannelStartTimeUpdate as VoiceChannelStartTimeUpdateModel
lazy from wd_discord.gateway.events import VoiceChannelStatusUpdate as VoiceChannelStatusUpdateModel


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.permissions import ChannelType


class GuildDelete(Entity[GuildDeleteModel]):
    """GUILD_DELETE: the bot left or was removed from a guild, or the guild went offline."""

    @property
    def guild(self) -> PartialGuild:
        """The guild the bot lost."""
        return PartialGuild(self.client, self.model.id)

    @property
    def unavailable(self) -> bool:
        """Whether the guild only went offline; it comes back as a GUILD_CREATE. ``False`` when the bot left it."""
        return bool(self.model.unavailable)


class ChannelPinsUpdate(Entity[ChannelPinsUpdateModel]):
    """CHANNEL_PINS_UPDATE: a message in a channel was pinned or unpinned."""

    @property
    def channel(self) -> PartialChannel:
        """The channel whose pins changed."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def last_pin_timestamp(self) -> datetime | None:
        """When the newest pinned message was pinned; ``None`` once nothing is pinned."""
        return self.model.last_pin_timestamp


class ThreadCreate(Entity[ThreadCreateModel]):
    """THREAD_CREATE: a thread was created, or the bot was added to a private thread."""

    @property
    def thread(self) -> Channel:
        """The thread."""
        return Channel(self.client, self.model)

    @property
    def newly_created(self) -> bool:
        """Whether the thread is new; ``False`` when the bot was added to an existing private thread."""
        return bool(self.model.newly_created)


class ThreadDelete(Entity[ThreadDeleteModel]):
    """THREAD_DELETE: a thread the bot could see was deleted."""

    @property
    def thread(self) -> PartialChannel:
        """The deleted thread."""
        return PartialChannel(self.client, self.model.id)

    @property
    def guild(self) -> PartialGuild:
        """The thread's guild."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def parent(self) -> PartialChannel | None:
        """The channel the thread was in."""
        parent_id = self.model.parent_id
        return None if parent_id is None else PartialChannel(self.client, parent_id)

    @property
    def type(self) -> ChannelType:
        """The kind of thread it was."""
        return self.model.type


class ThreadListSync(Entity[ThreadListSyncModel]):
    """THREAD_LIST_SYNC: the bot gained access to channels, and these are their active threads."""

    @property
    def guild(self) -> PartialGuild:
        """The guild of the synced channels."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def channels(self) -> Generator[PartialChannel] | None:
        """The channels whose threads were synced; ``None`` when it's the whole guild.

        A channel listed here without threads in :attr:`threads` has none, so any the bot knew of are stale.
        """
        channel_ids = self.model.channel_ids
        if channel_ids is None:
            return None
        return (PartialChannel(self.client, channel_id) for channel_id in channel_ids)

    @property
    def threads(self) -> Generator[Channel]:
        """The active threads in the synced channels."""
        for thread in self.model.threads:
            yield Channel(self.client, thread)

    @property
    def members(self) -> Generator[ThreadMember]:
        """The bot's own membership of each of :attr:`threads` it has joined."""
        for member in self.model.members:
            if member.id is not None:
                yield ThreadMember(self.client, member, member.id)


class ThreadMembersUpdate(Entity[ThreadMembersUpdateModel]):
    """THREAD_MEMBERS_UPDATE: members joined or left a thread."""

    @property
    def thread(self) -> PartialChannel:
        """The thread whose members changed."""
        return PartialChannel(self.client, self.model.id)

    @property
    def guild(self) -> PartialGuild:
        """The thread's guild."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def member_count(self) -> int:
        """Roughly how many members the thread has; stops counting at 50."""
        return self.model.member_count

    @property
    def added_members(self) -> Generator[Member]:
        """The guild members who joined the thread."""
        for added in self.model.added_members or []:
            yield Member(self.client, added.member, self.model.guild_id)

    @property
    def removed_members(self) -> Generator[PartialMember]:
        """The members who left the thread."""
        for user_id in self.model.removed_member_ids or []:
            yield PartialMember(self.client, user_id, self.model.guild_id)


class VoiceChannelStatusUpdate(Entity[VoiceChannelStatusUpdateModel]):
    """VOICE_CHANNEL_STATUS_UPDATE: a voice channel's status was set or cleared."""

    @property
    def channel(self) -> PartialChannel:
        """The voice channel."""
        return PartialChannel(self.client, self.model.id)

    @property
    def guild(self) -> PartialGuild:
        """The voice channel's guild."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def status(self) -> str | None:
        """The channel's new status; ``None`` once cleared."""
        return self.model.status


class VoiceChannelStartTimeUpdate(Entity[VoiceChannelStartTimeUpdateModel]):
    """VOICE_CHANNEL_START_TIME_UPDATE: a voice session in a channel started or ended."""

    @property
    def channel(self) -> PartialChannel:
        """The voice channel."""
        return PartialChannel(self.client, self.model.id)

    @property
    def guild(self) -> PartialGuild:
        """The voice channel's guild."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def voice_start_time(self) -> datetime | None:
        """When the channel's current voice session started; ``None`` once nobody is in it."""
        seconds = self.model.voice_start_time
        return None if seconds is None else datetime.fromtimestamp(seconds, UTC)
