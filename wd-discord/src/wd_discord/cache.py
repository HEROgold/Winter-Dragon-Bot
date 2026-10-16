"""The client's view of Discord, kept current by the gateway.

:meth:`StateCache.apply` takes every parsed dispatch: GUILD_CREATE lays down a guild's channels, roles, members and
voice states, and the events after it add, change and remove entries. Entities read it to answer without a request
(``guild.get_role(id)``). It holds the data models, not entities, so each read wraps the latest data.

A collection that is ``None`` isn't known (a guild only fetched over REST has no channels yet); an empty one is known
to be empty. A guild's members are only complete when Discord sent them all, which it does below ``large_threshold``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
lazy from functools import cache
lazy from typing import TYPE_CHECKING

from wd_discord.resources.guild import Emoji, GuildMember, Role, Sticker
from wd_discord.snowflake import Snowflake
lazy from wd_discord.gateway import events as wire


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from wd_discord.gateway.presence import Presence
    from wd_discord.models import DiscordModel
    from wd_discord.resources.channel.channel import Channel
    from wd_discord.resources.guild import Guild
    from wd_discord.resources.user import User
    from wd_discord.resources.voice import VoiceState


@dataclass
class GuildState:
    """What the client knows of one guild."""

    guild: Guild
    """The guild's own data, as last sent."""
    unavailable: bool = False
    """Whether the guild is offline; its data is from before the outage."""
    channels: dict[Snowflake, Channel] | None = None
    threads: dict[Snowflake, Channel] | None = None
    roles: dict[Snowflake, Role] = field(default_factory=dict[Snowflake, Role])
    emojis: dict[Snowflake, Emoji] = field(default_factory=dict[Snowflake, Emoji])
    stickers: dict[Snowflake, Sticker] = field(default_factory=dict[Snowflake, Sticker])
    members: dict[Snowflake, GuildMember] = field(default_factory=dict[Snowflake, GuildMember])
    """The members seen so far; every member only when :attr:`members_complete`."""
    members_complete: bool = False
    voice_states: dict[Snowflake, VoiceState] | None = None
    """Who is in a voice channel, by user ID."""
    presences: dict[Snowflake, Presence] | None = None
    """The members' presences, by user ID."""

    def set_guild(self, guild: Guild) -> None:
        """Take ``guild`` as the guild's data, with the roles, emojis and stickers it carries."""
        self.guild = guild
        self.roles = {role.id: role for role in guild.roles}
        self.emojis = {emoji.id: emoji for emoji in guild.emojis if emoji.id is not None}
        self.stickers = {sticker.id: sticker for sticker in guild.stickers or []}


class StateCache:
    """Every guild, channel and the bot's own user, as the gateway last described them."""

    def __init__(self) -> None:
        """Start knowing nothing."""
        self.guilds: dict[Snowflake, GuildState] = {}
        self.private_channels: dict[Snowflake, Channel] = {}
        """DM and group DM channels, which belong to no guild."""
        self.user: User | None = None
        """The bot's own user, from READY and USER_UPDATE."""
        self._channel_guilds: dict[Snowflake, Snowflake] = {}
        """The guild of each known guild channel and thread."""

    # --- Reading -------------------------------------------------------------------

    def guild(self, guild_id: Snowflake) -> GuildState | None:
        """Return what's known of the guild ``guild_id``, or ``None``."""
        return self.guilds.get(guild_id)

    def channel(self, channel_id: Snowflake) -> Channel | None:
        """Return the guild channel, thread or DM ``channel_id``, or ``None``."""
        guild_id = self._channel_guilds.get(channel_id)
        if guild_id is None:
            return self.private_channels.get(channel_id)
        state = self.guilds.get(guild_id)
        if state is None:
            return None
        return (state.channels or {}).get(channel_id) or (state.threads or {}).get(channel_id)

    # --- Remembering REST answers ---------------------------------------------------

    def store_guild(self, guild: Guild) -> None:
        """Take a fetched ``guild`` as the latest data of it, with its roles, emojis and stickers."""
        state = self.guilds.get(guild.id)
        if state is None:
            self.guilds[guild.id] = state = GuildState(guild=guild)
        state.set_guild(guild)

    def store_channels(self, guild_id: Snowflake, channels: Iterable[Channel]) -> None:
        """Take ``channels`` as every channel of a known guild, threads excluded."""
        state = self.guilds.get(guild_id)
        if state is None:
            return
        for channel_id in state.channels or {}:
            self._channel_guilds.pop(channel_id, None)
        state.channels = {channel.id: channel.model_copy(update={"guild_id": guild_id}) for channel in channels}
        self._channel_guilds.update(dict.fromkeys(state.channels, guild_id))

    def store_roles(self, guild_id: Snowflake, roles: Iterable[Role]) -> None:
        """Take ``roles`` as every role of a known guild."""
        state = self.guilds.get(guild_id)
        if state is not None:
            state.roles = {role.id: role for role in roles}

    def store_emojis(self, guild_id: Snowflake, emojis: Iterable[Emoji]) -> None:
        """Take ``emojis`` as every custom emoji of a known guild."""
        state = self.guilds.get(guild_id)
        if state is not None:
            state.emojis = {emoji.id: emoji for emoji in emojis if emoji.id is not None}

    def store_stickers(self, guild_id: Snowflake, stickers: Iterable[Sticker]) -> None:
        """Take ``stickers`` as every sticker of a known guild."""
        state = self.guilds.get(guild_id)
        if state is not None:
            state.stickers = {sticker.id: sticker for sticker in stickers}

    def store_members(self, guild_id: Snowflake, members: Iterable[GuildMember]) -> None:
        """Add or replace ``members`` of a known guild; the others stay as they were."""
        state = self.guilds.get(guild_id)
        if state is not None:
            state.members.update((member.user.id, member) for member in members if member.user is not None)

    # --- Applying gateway events -----------------------------------------------------

    def apply(self, model: DiscordModel) -> DiscordModel | None:
        """Bring the cache up to date with a parsed dispatch ``model``.

        Returns what the event replaced or removed (the channel before a CHANNEL_UPDATE, the role a
        GUILD_ROLE_DELETE deleted), or ``None`` when it replaced nothing the cache knew.
        """
        handler = self._handlers().get(type(model))
        return None if handler is None else handler(self, model)

    @classmethod
    @cache
    def _handlers(cls) -> Mapping[type[DiscordModel], Callable[..., DiscordModel | None]]:
        """Return how each dispatch model changes the cache, keyed by the model's exact class."""
        return {
            wire.Ready: cls._ready,
            wire.GuildCreate: cls._guild_create,
            wire.GuildUpdate: cls._guild_update,
            wire.GuildDelete: cls._guild_delete,
            wire.ChannelCreate: cls._channel_upsert,
            wire.ChannelUpdate: cls._channel_upsert,
            wire.ChannelDelete: cls._channel_delete,
            wire.ChannelPinsUpdate: cls._channel_pins_update,
            wire.ThreadCreate: cls._channel_upsert,
            wire.ThreadUpdate: cls._channel_upsert,
            wire.ThreadDelete: cls._channel_delete,
            wire.ThreadListSync: cls._thread_list_sync,
            wire.ThreadMemberUpdate: cls._thread_member_update,
            wire.ThreadMembersUpdate: cls._thread_members_update,
            wire.GuildMemberAdd: cls._member_add,
            wire.GuildMemberRemove: cls._member_remove,
            wire.GuildMemberUpdate: cls._member_update,
            wire.GuildMembersChunk: cls._members_chunk,
            wire.GuildRoleCreate: cls._role_upsert,
            wire.GuildRoleUpdate: cls._role_upsert,
            wire.GuildRoleDelete: cls._role_delete,
            wire.UserUpdate: cls._user_update,
            wire.PresenceUpdate: cls._presence_update,
            wire.VoiceStateUpdate: cls._voice_state_update,
        }

    def _ready(self, model: wire.Ready) -> None:
        self.user = model.user

    def _guild_create(self, model: wire.GuildCreate) -> Guild | None:
        previous = self.guilds.get(model.id)
        if previous is not None:
            self._forget_channels(previous)
        # The lists move into the state's own collections; keeping them on the guild too would hold a stale copy.
        lists: dict[str, list[object]] = {"channels": [], "threads": [], "members": [], "voice_states": [], "presences": []}
        state = GuildState(guild=model.model_copy(update=lists))
        state.set_guild(state.guild)
        state.channels = {channel.id: channel.model_copy(update={"guild_id": model.id}) for channel in model.channels}
        state.threads = {thread.id: thread.model_copy(update={"guild_id": model.id}) for thread in model.threads}
        state.members = {member.user.id: member for member in model.members if member.user is not None}
        state.members_complete = not model.large
        state.voice_states = {voice.user_id: voice.model_copy(update={"guild_id": model.id}) for voice in model.voice_states}
        state.presences = {presence.user.id: presence for presence in model.presences}
        self.guilds[model.id] = state
        self._channel_guilds.update(dict.fromkeys([*state.channels, *state.threads], model.id))
        return None if previous is None else previous.guild

    def _guild_update(self, model: wire.GuildUpdate) -> Guild | None:
        state = self.guilds.get(model.id)
        if state is None:
            self.guilds[model.id] = state = GuildState(guild=model)
            state.set_guild(model)
            return None
        previous = state.guild
        state.set_guild(model)
        return previous

    def _guild_delete(self, model: wire.GuildDelete) -> Guild | None:
        state = self.guilds.get(model.id)
        if state is None:
            return None
        if model.unavailable:
            state.unavailable = True
            return None
        del self.guilds[model.id]
        self._forget_channels(state)
        return state.guild

    def _channel_upsert(self, model: Channel) -> Channel | None:
        guild_id = model.guild_id
        if guild_id is None:
            previous = self.private_channels.get(model.id)
            self.private_channels[model.id] = model
            return previous
        state = self.guilds.get(guild_id)
        if state is None:
            return None
        is_thread = model.thread_metadata is not None
        known = state.threads if is_thread else state.channels
        if known is None:
            return None
        previous = known.get(model.id)
        known[model.id] = model
        self._channel_guilds[model.id] = guild_id
        return previous

    def _channel_delete(self, model: Channel | wire.ThreadDelete) -> Channel | None:
        self._channel_guilds.pop(model.id, None)
        if model.guild_id is None:
            return self.private_channels.pop(model.id, None)
        state = self.guilds.get(model.guild_id)
        if state is None:
            return None
        removed = (state.channels or {}).pop(model.id, None)
        return removed or (state.threads or {}).pop(model.id, None)

    def _channel_pins_update(self, model: wire.ChannelPinsUpdate) -> Channel | None:
        channel = self.channel(model.channel_id)
        if channel is None:
            return None
        self._channel_upsert(channel.model_copy(update={"last_pin_timestamp": model.last_pin_timestamp}))
        return channel

    def _thread_list_sync(self, model: wire.ThreadListSync) -> None:
        state = self.guilds.get(model.guild_id)
        if state is None or state.threads is None:
            return
        synced = None if model.channel_ids is None else set(model.channel_ids)
        stale = [thread_id for thread_id, thread in state.threads.items() if synced is None or thread.parent_id in synced]
        for thread_id in stale:
            del state.threads[thread_id]
            self._channel_guilds.pop(thread_id, None)
        memberships = {member.id: member for member in model.members}
        for thread in model.threads:
            member = memberships.get(thread.id)
            update = {"guild_id": model.guild_id} if member is None else {"guild_id": model.guild_id, "member": member}
            self._channel_upsert(thread.model_copy(update=update))

    def _thread_member_update(self, model: wire.ThreadMemberUpdate) -> Channel | None:
        thread = self.channel(model.id)
        if thread is None:
            return None
        self._channel_upsert(thread.model_copy(update={"member": model}))
        return thread

    def _thread_members_update(self, model: wire.ThreadMembersUpdate) -> Channel | None:
        thread = self.channel(model.id)
        if thread is None:
            return None
        self._channel_upsert(thread.model_copy(update={"member_count": model.member_count}))
        return thread

    def _member_add(self, model: wire.GuildMemberAdd) -> GuildMember | None:
        state = self.guilds.get(model.guild_id)
        if state is None or model.user is None:
            return None
        previous = state.members.get(model.user.id)
        state.members[model.user.id] = model
        return previous

    def _member_remove(self, model: wire.GuildMemberRemove) -> GuildMember | None:
        state = self.guilds.get(model.guild_id)
        if state is None:
            return None
        if state.presences is not None:
            state.presences.pop(model.user.id, None)
        return state.members.pop(model.user.id, None)

    def _member_update(self, model: wire.GuildMemberUpdate) -> GuildMember | None:
        """Merge the partial member into the one cached; a member not cached yet stays unknown."""
        state = self.guilds.get(model.guild_id)
        previous = None if state is None else state.members.get(model.user.id)
        if state is None or previous is None:
            return None
        changes = {name: getattr(model, name) for name in model.model_fields_set if name != "guild_id"}
        state.members[model.user.id] = previous.model_copy(update=changes)
        return previous

    def _members_chunk(self, model: wire.GuildMembersChunk) -> None:
        state = self.guilds.get(model.guild_id)
        if state is None:
            return
        state.members.update((member.user.id, member) for member in model.members if member.user is not None)
        if state.presences is not None:
            state.presences.update((presence.user.id, presence) for presence in model.presences or [])

    def _role_upsert(self, model: wire.GuildRoleCreate | wire.GuildRoleUpdate) -> Role | None:
        state = self.guilds.get(model.guild_id)
        if state is None:
            return None
        previous = state.roles.get(model.role.id)
        state.roles[model.role.id] = model.role
        return previous

    def _role_delete(self, model: wire.GuildRoleDelete) -> Role | None:
        """Drop the role, and take it off every member who had it, as Discord sends no member update for that."""
        state = self.guilds.get(model.guild_id)
        if state is None:
            return None
        for user_id, member in state.members.items():
            if model.role_id in member.roles:
                roles = [role for role in member.roles if role != model.role_id]
                state.members[user_id] = member.model_copy(update={"roles": roles})
        return state.roles.pop(model.role_id, None)

    def _user_update(self, model: wire.UserUpdate) -> User | None:
        previous = self.user
        self.user = model
        return previous

    def _presence_update(self, model: wire.PresenceUpdate) -> Presence | None:
        state = None if model.guild_id is None else self.guilds.get(model.guild_id)
        if state is None or state.presences is None:
            return None
        previous = state.presences.get(model.user.id)
        state.presences[model.user.id] = model
        return previous

    def _voice_state_update(self, model: wire.VoiceStateUpdate) -> VoiceState | None:
        """Track who is in voice; a member sent along is the latest of them too."""
        state = None if model.guild_id is None else self.guilds.get(model.guild_id)
        if state is None:
            return None
        if model.member is not None:
            state.members[model.user_id] = model.member
        if state.voice_states is None:
            return None
        if model.channel_id is None:
            return state.voice_states.pop(model.user_id, None)
        previous = state.voice_states.get(model.user_id)
        state.voice_states[model.user_id] = model
        return previous

    def _forget_channels(self, state: GuildState) -> None:
        for channel_id in [*(state.channels or {}), *(state.threads or {})]:
            self._channel_guilds.pop(channel_id, None)
