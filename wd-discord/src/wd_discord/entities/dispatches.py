"""Gateway events that are about more than one entity, bound to the client that received them.

An event about one thing binds to that thing (CHANNEL_CREATE is a :class:`~wd_discord.entities.channel.Channel`).
The events here carry several, or facts besides the entity (GUILD_DELETE says whether the guild only went offline),
so each gets its own class exposing the entities as relations next to those facts.
"""

from dataclasses import dataclass
lazy from datetime import UTC, datetime
lazy from typing import TYPE_CHECKING

lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import Channel, PartialChannel, ThreadMember
lazy from wd_discord.entities.emoji import Emoji, Sticker
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.entities.message import PartialMessage
lazy from wd_discord.entities.presence import Presence
lazy from wd_discord.entities.user import PartialUser, User
lazy from wd_discord.gateway.events import ChannelPinsUpdate as ChannelPinsUpdateModel
lazy from wd_discord.gateway.events import GuildDelete as GuildDeleteModel
lazy from wd_discord.gateway.events import GuildEmojisUpdate as GuildEmojisUpdateModel
lazy from wd_discord.gateway.events import GuildMemberRemove as GuildMemberRemoveModel
lazy from wd_discord.gateway.events import GuildMembersChunk as GuildMembersChunkModel
lazy from wd_discord.gateway.events import GuildStickersUpdate as GuildStickersUpdateModel
lazy from wd_discord.gateway.events import MessageDelete as MessageDeleteModel
lazy from wd_discord.gateway.events import MessageDeleteBulk as MessageDeleteBulkModel
lazy from wd_discord.gateway.events import MessageReactionAdd as MessageReactionAddModel
lazy from wd_discord.gateway.events import MessageReactionRemove as MessageReactionRemoveModel
lazy from wd_discord.gateway.events import MessageReactionRemoveAll as MessageReactionRemoveAllModel
lazy from wd_discord.gateway.events import MessageReactionRemoveEmoji as MessageReactionRemoveEmojiModel
lazy from wd_discord.gateway.events import ThreadCreate as ThreadCreateModel
lazy from wd_discord.gateway.events import ThreadDelete as ThreadDeleteModel
lazy from wd_discord.gateway.events import ThreadListSync as ThreadListSyncModel
lazy from wd_discord.gateway.events import ThreadMembersUpdate as ThreadMembersUpdateModel
lazy from wd_discord.gateway.events import TypingStart as TypingStartModel
lazy from wd_discord.gateway.events import VoiceChannelStartTimeUpdate as VoiceChannelStartTimeUpdateModel
lazy from wd_discord.gateway.events import VoiceChannelStatusUpdate as VoiceChannelStatusUpdateModel


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.partial_emoji import PartialEmoji
    from wd_discord.permissions import ChannelType
    from wd_discord.resources.guild import GuildMember


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
        return self._partial(PartialGuild, self.model.guild_id)

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
        return self._partial(PartialChannel, self.model.parent_id)

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


@dataclass(frozen=True)
class MemberRemove(Entity[GuildMemberRemoveModel]):
    """GUILD_MEMBER_REMOVE: someone left a guild, or was kicked or banned from it."""

    _left: GuildMember | None = None
    """The membership the client's cache held until this event; the event itself names only the user."""

    @property
    def guild(self) -> PartialGuild:
        """The guild they left."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def user(self) -> User:
        """Who left."""
        return User(self.client, self.model.user)

    @property
    def member(self) -> Member | None:
        """The member as they were before leaving, roles included; ``None`` when the cache didn't know them."""
        return None if self._left is None else Member(self.client, self._left, self.model.guild_id)


class MembersChunk(Entity[GuildMembersChunkModel]):
    """GUILD_MEMBERS_CHUNK: one part of the members a Request Guild Members (opcode 8) asked for."""

    @property
    def guild(self) -> PartialGuild:
        """The guild the members are from."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def members(self) -> Generator[Member]:
        """The members in this chunk."""
        for member in self.model.members:
            yield Member(self.client, member, self.model.guild_id)

    @property
    def chunk_index(self) -> int:
        """Which chunk this is, from ``0``."""
        return self.model.chunk_index

    @property
    def chunk_count(self) -> int:
        """How many chunks the answer has."""
        return self.model.chunk_count

    @property
    def not_found(self) -> Generator[PartialUser]:
        """The requested users who aren't members of the guild."""
        for user_id in self.model.not_found or []:
            yield PartialUser(self.client, user_id)

    @property
    def presences(self) -> Generator[Presence]:
        """The members' presences, when the request asked for them."""
        for presence in self.model.presences or []:
            yield Presence(self.client, presence)

    @property
    def nonce(self) -> str | None:
        """The nonce the request was sent with, to match the chunks to it."""
        return self.model.nonce


class MessageDelete(Entity[MessageDeleteModel]):
    """MESSAGE_DELETE: a message was deleted."""

    @property
    def message(self) -> PartialMessage:
        """The deleted message."""
        return PartialMessage(self.client, self.model.id, self.model.channel_id)

    @property
    def channel(self) -> PartialChannel:
        """The channel it was in."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)


class MessageDeleteBulk(Entity[MessageDeleteBulkModel]):
    """MESSAGE_DELETE_BULK: several messages of one channel were deleted at once."""

    @property
    def messages(self) -> Generator[PartialMessage]:
        """The deleted messages."""
        for message_id in self.model.ids:
            yield PartialMessage(self.client, message_id, self.model.channel_id)

    @property
    def channel(self) -> PartialChannel:
        """The channel they were in."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)


class ReactionAdd(Entity[MessageReactionAddModel]):
    """MESSAGE_REACTION_ADD: someone reacted to a message."""

    @property
    def user(self) -> PartialUser:
        """Who reacted."""
        return PartialUser(self.client, self.model.user_id)

    @property
    def member(self) -> Member | None:
        """Who reacted, as a member of the guild; ``None`` in a DM."""
        member, guild_id = self.model.member, self.model.guild_id
        return None if member is None or guild_id is None else Member(self.client, member, guild_id)

    @property
    def message(self) -> PartialMessage:
        """The message reacted to."""
        return PartialMessage(self.client, self.model.message_id, self.model.channel_id)

    @property
    def message_author(self) -> PartialUser | None:
        """Who sent the message reacted to, when Discord says."""
        return self._partial(PartialUser, self.model.message_author_id)

    @property
    def channel(self) -> PartialChannel:
        """The message's channel."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)

    @property
    def emoji(self) -> PartialEmoji:
        """The emoji reacted with."""
        return self.model.emoji

    @property
    def burst(self) -> bool:
        """Whether it is a super reaction."""
        return self.model.burst


class ReactionRemove(Entity[MessageReactionRemoveModel]):
    """MESSAGE_REACTION_REMOVE: someone removed their reaction from a message."""

    @property
    def user(self) -> PartialUser:
        """Whose reaction was removed."""
        return PartialUser(self.client, self.model.user_id)

    @property
    def message(self) -> PartialMessage:
        """The message the reaction was on."""
        return PartialMessage(self.client, self.model.message_id, self.model.channel_id)

    @property
    def channel(self) -> PartialChannel:
        """The message's channel."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)

    @property
    def emoji(self) -> PartialEmoji:
        """The emoji of the removed reaction."""
        return self.model.emoji

    @property
    def burst(self) -> bool:
        """Whether it was a super reaction."""
        return self.model.burst


class ReactionRemoveAll(Entity[MessageReactionRemoveAllModel]):
    """MESSAGE_REACTION_REMOVE_ALL: every reaction on a message was removed."""

    @property
    def message(self) -> PartialMessage:
        """The message cleared of reactions."""
        return PartialMessage(self.client, self.model.message_id, self.model.channel_id)

    @property
    def channel(self) -> PartialChannel:
        """The message's channel."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)


class ReactionRemoveEmoji(Entity[MessageReactionRemoveEmojiModel]):
    """MESSAGE_REACTION_REMOVE_EMOJI: every reaction with one emoji was removed from a message."""

    @property
    def message(self) -> PartialMessage:
        """The message the reactions were on."""
        return PartialMessage(self.client, self.model.message_id, self.model.channel_id)

    @property
    def channel(self) -> PartialChannel:
        """The message's channel."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)

    @property
    def emoji(self) -> PartialEmoji:
        """The emoji whose reactions were removed."""
        return self.model.emoji


class TypingStart(Entity[TypingStartModel]):
    """TYPING_START: someone started typing in a channel."""

    @property
    def user(self) -> PartialUser:
        """Who is typing."""
        return PartialUser(self.client, self.model.user_id)

    @property
    def member(self) -> Member | None:
        """Who is typing, as a member of the guild; ``None`` in a DM."""
        member, guild_id = self.model.member, self.model.guild_id
        return None if member is None or guild_id is None else Member(self.client, member, guild_id)

    @property
    def channel(self) -> PartialChannel:
        """Where they are typing."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def guild(self) -> PartialGuild | None:
        """The channel's guild; ``None`` for a DM."""
        return self._partial(PartialGuild, self.model.guild_id)

    @property
    def started_at(self) -> datetime:
        """When they started typing."""
        return datetime.fromtimestamp(self.model.timestamp, UTC)


class GuildEmojisUpdate(Entity[GuildEmojisUpdateModel]):
    """GUILD_EMOJIS_UPDATE: a guild's emojis changed; this is its full new list."""

    @property
    def guild(self) -> PartialGuild:
        """The guild."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def emojis(self) -> Generator[Emoji]:
        """Every emoji the guild has now."""
        for emoji in self.model.emojis:
            yield Emoji(self.client, emoji, self.model.guild_id)


class GuildStickersUpdate(Entity[GuildStickersUpdateModel]):
    """GUILD_STICKERS_UPDATE: a guild's stickers changed; this is its full new list."""

    @property
    def guild(self) -> PartialGuild:
        """The guild."""
        return PartialGuild(self.client, self.model.guild_id)

    @property
    def stickers(self) -> Generator[Sticker]:
        """Every sticker the guild has now."""
        for sticker in self.model.stickers:
            yield Sticker(self.client, sticker)
