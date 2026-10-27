"""Guilds (https://docs.discord.com/developers/resources/guild)."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Any, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.cache import StateCache
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, every_page, no_content, parse, parse_all
lazy from wd_discord.entities.channel import Channel, PartialChannel
lazy from wd_discord.entities.emoji import Emoji, Sticker
lazy from wd_discord.entities.invite import Invite
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.entities.role import PartialRole, Role
lazy from wd_discord.entities.voice import VoiceState
lazy from wd_discord.permission_solver import PermissionSolver
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.guild import Emoji as EmojiModel
lazy from wd_discord.resources.guild import Guild as GuildModel
lazy from wd_discord.resources.guild import GuildMember
lazy from wd_discord.resources.guild import Role as RoleModel
lazy from wd_discord.resources.guild import Sticker as StickerModel
lazy from wd_discord.resources.guild import WelcomeScreen as WelcomeScreenModel
lazy from wd_discord.resources.guild import WelcomeScreenChannel as WelcomeScreenChannelModel
lazy from wd_discord.resources.invite import Invite as InviteModel
lazy from wd_discord.resources.voice import VoiceState as VoiceStateModel
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from string.templatelib import Template

    from wd_discord.audit import Reason
    from wd_discord.cache import GuildState
    from wd_discord.client import Client, NetworkError, RequestResult
    from wd_discord.entities.member import BaseMember
    from wd_discord.entities.user import BaseUser
    from wd_discord.gateway.events import GuildCreate
    from wd_discord.image import ImageHash
    from wd_discord.models import DiscordModel
    from wd_discord.partial_emoji import PartialEmoji
    from wd_discord.resources.channel import GuildChannelParams
    from wd_discord.resources.guild import (
        MFALevel,
        NSFWLevel,
        PremiumTier,
        VerificationLevel,
    )
    from wd_discord.snowflake import SnowflakeLike


MAX_MEMBERS_PER_PAGE = 1000
"""The most members ``GET /guilds/{guild_id}/members`` returns at once (https://docs.discord.com/developers/resources/guild#list-guild-members)."""


class BaseGuild(ClientBound):
    """What can be done to a guild knowing only its ID: read it, its channels, members, roles and expressions."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    # --- From the client's cache: no request, ``None`` when the client doesn't know it -----------

    @property
    def _state(self) -> GuildState | None:
        return self.client.cache.guild(self.id)

    @property
    def cached(self) -> Guild | None:
        """The guild as the client last saw it, from the gateway or a fetch."""
        state = self._state
        return None if state is None else Guild(self.client, state.current_guild())

    @property
    def channels(self) -> Generator[Channel] | None:
        """The guild's channels, threads excluded."""
        state = self._state
        if state is None or state.channels is None:
            return None
        return (Channel(self.client, channel) for channel in state.channels.values())

    @property
    def threads(self) -> Generator[Channel] | None:
        """The guild's active threads the bot can see."""
        state = self._state
        if state is None or state.threads is None:
            return None
        return (Channel(self.client, thread) for thread in state.threads.values())

    @property
    def members(self) -> Generator[Member] | None:
        """Every member of the guild; ``None`` unless the client has them all (see :meth:`get_member`)."""
        state = self._state
        if state is None or not state.members_complete:
            return None
        return (Member(self.client, member, self.id) for member in state.members.values())

    @property
    def roles(self) -> Generator[Role] | None:
        """The guild's roles, ``@everyone`` included."""
        state = self._state
        return None if state is None else (Role(self.client, role, self.id) for role in state.roles.values())

    @property
    def emojis(self) -> Generator[Emoji] | None:
        """The guild's custom emojis."""
        state = self._state
        return None if state is None else (Emoji(self.client, emoji, self.id) for emoji in state.emojis.values())

    @property
    def stickers(self) -> Generator[Sticker] | None:
        """The guild's own stickers."""
        state = self._state
        return None if state is None else (Sticker(self.client, sticker) for sticker in state.stickers.values())

    @property
    def voice_states(self) -> Generator[VoiceState] | None:
        """Who is in which of the guild's voice channels."""
        state = self._state
        if state is None or state.voice_states is None:
            return None
        return (VoiceState(self.client, voice) for voice in state.voice_states.values())

    def get_channel(self, channel_id: SnowflakeLike) -> Channel | None:
        """Return the channel or thread ``channel_id`` of the guild if the client knows it."""
        channel = self.client.cache.channel(Snowflake.coerce(channel_id))
        return None if channel is None or channel.guild_id != self.id else Channel(self.client, channel)

    def get_member(self, user_id: SnowflakeLike) -> Member | None:
        """Return the member ``user_id`` if the client has seen them; in a large guild it may not have."""
        state = self._state
        member = None if state is None else state.members.get(Snowflake.coerce(user_id))
        return None if member is None else Member(self.client, member, self.id)

    def get_role(self, role_id: SnowflakeLike) -> Role | None:
        """Return the role ``role_id`` if the client knows it."""
        state = self._state
        role = None if state is None else state.roles.get(Snowflake.coerce(role_id))
        return None if role is None else Role(self.client, role, self.id)

    def get_emoji(self, emoji_id: SnowflakeLike) -> Emoji | None:
        """Return the custom emoji ``emoji_id`` if the client knows it."""
        state = self._state
        emoji = None if state is None else state.emojis.get(Snowflake.coerce(emoji_id))
        return None if emoji is None else Emoji(self.client, emoji, self.id)

    def get_voice_state(self, member: BaseMember | BaseUser) -> VoiceState | None:
        """Return ``member``'s voice state here if the client knows they're in a voice channel."""
        state = self._state
        voice = None if state is None or state.voice_states is None else state.voice_states.get(member.id)
        return None if voice is None else VoiceState(self.client, voice)

    async def own_permissions(self) -> PermissionSolver | NetworkError:
        """Return what the client's own member may do in the guild, roles to give included.

        Reads the guild, the client's own user and its member here from the cache, fetching each one it doesn't know
        once; every fetch fills the cache, so the next call needs none.
        """
        guild = self.cached
        if guild is None:
            guild = await self.fetch(cache=True)
            if is_network_error(guild):
                return guild
        me = self.client.cache.user
        if me is None:
            current = await self.client.users.me()
            if is_network_error(current):
                return current
            me = current.model
        own = self.get_member(me.id)
        if own is None:
            own = await self.member(me.id).fetch(cache=True)
            if is_network_error(own):
                return own
        return PermissionSolver(guild.model, own.model)

    # --- From Discord: a request each, whose answer also updates the cache ------------------------

    async def _stored[M: DiscordModel, E: Entity[Any]](  # noqa: PLR0913 - route, model, store and entity are each one step
        self,
        route: Template,
        model: type[M],
        store: Callable[[StateCache, Snowflake, list[M]], object],
        entity: type[E],
        *args: object,
        params: dict[str, str] | None = None,
        cache: bool = False,
    ) -> Generator[E] | NetworkError:
        """GET ``route`` as a list of ``model``; ``store`` it in the state cache, then wrap each item as ``entity``.

        ``store`` is a :class:`~wd_discord.cache.StateCache` method taking this guild's ID, and ``args`` follow
        the client and the item in ``entity``'s call. A failure leaves the cache as it was.
        """
        parsed = parse_all(await self.client.get(route, params=params or {}, cache=cache), model)
        if is_network_error(parsed):
            return parsed
        store(self.client.cache, self.id, parsed)
        return (entity(self.client, item, *args) for item in parsed)

    async def fetch(self, *, with_counts: bool = False, cache: bool = False) -> Guild | NetworkError:
        """GET /guilds/{guild_id}; ``with_counts`` fills in the approximate member and online counts."""
        params = {"with_counts": "true"} if with_counts else {}
        parsed = parse(await self.client.get(t"/guilds/{self.id}", params=params, cache=cache), GuildModel)
        if is_network_error(parsed):
            return parsed
        self.client.cache.store_guild(parsed)
        return Guild(self.client, parsed)

    def channel(self, channel_id: SnowflakeLike) -> PartialChannel:
        """Return a handle on the channel ``channel_id``, without fetching it."""
        return PartialChannel(self.client, Snowflake.coerce(channel_id))

    async def fetch_channels(self, *, cache: bool = False) -> Generator[Channel] | NetworkError:
        """GET /guilds/{guild_id}/channels - the guild's channels, threads excluded."""
        return await self._stored(t"/guilds/{self.id}/channels", ChannelModel, StateCache.store_channels, Channel, cache=cache)

    async def create_channel(
        self,
        params: GuildChannelParams,
        *,
        reason: Reason = None,
    ) -> Channel | NetworkError:
        """POST /guilds/{guild_id}/channels - create a channel or category; needs MANAGE_CHANNELS."""
        result = await self.client.post(t"/guilds/{self.id}/channels", json=params.to_json(), headers=reason_headers(reason))
        return self._entity(result, ChannelModel, Channel)

    def member(self, user_id: SnowflakeLike) -> PartialMember:
        """Return a handle on the member ``user_id`` of this guild, without fetching them."""
        return PartialMember(self.client, Snowflake.coerce(user_id), self.id)

    async def fetch_members(
        self,
        *,
        after: BaseMember | BaseUser | None = None,
        limit: int = MAX_MEMBERS_PER_PAGE,
        cache: bool = False,
    ) -> Generator[Member] | NetworkError:
        """GET /guilds/{guild_id}/members - one page of members, by user ID, after the member ``after``.

        Pass the last member of a page as ``after`` to get the next one; a page shorter than ``limit`` is the last.
        Needs the GUILD_MEMBERS intent.
        """
        params = {"limit": str(limit), "after": "0" if after is None else str(after.id)}
        route = t"/guilds/{self.id}/members"
        return await self._stored(route, GuildMember, StateCache.store_members, Member, self.id, params=params, cache=cache)

    async def all_members(
        self,
        *,
        page_size: int = MAX_MEMBERS_PER_PAGE,
        cache: bool = False,
    ) -> Generator[Member] | NetworkError:
        """Every member of the guild, by user ID, read ``page_size`` at a time; needs the GUILD_MEMBERS intent.

        ``page_size`` is capped at Discord's :data:`MAX_MEMBERS_PER_PAGE`, since a page shorter than it ends the list.
        """
        page_size = min(page_size, MAX_MEMBERS_PER_PAGE)
        members = await every_page(
            lambda after: self.fetch_members(after=after, limit=page_size, cache=cache),
            page_size,
        )
        if is_network_error(members):
            return members
        return (member for member in members)

    async def search_members(self, query: str, *, limit: int = 1) -> Generator[Member] | NetworkError:
        """GET /guilds/{guild_id}/members/search - the members whose username or nickname starts with ``query``."""
        params = {"query": query, "limit": str(limit)}
        return self._members(await self.client.get(t"/guilds/{self.id}/members/search", params=params))

    def role(self, role_id: SnowflakeLike) -> PartialRole:
        """Return a handle on the role ``role_id`` of this guild, without fetching it."""
        return PartialRole(self.client, Snowflake.coerce(role_id), self.id)

    async def fetch_roles(self, *, cache: bool = False) -> Generator[Role] | NetworkError:
        """GET /guilds/{guild_id}/roles - every role of the guild."""
        return await self._stored(t"/guilds/{self.id}/roles", RoleModel, StateCache.store_roles, Role, self.id, cache=cache)

    async def fetch_emojis(self, *, cache: bool = False) -> Generator[Emoji] | NetworkError:
        """GET /guilds/{guild_id}/emojis - the guild's custom emojis."""
        return await self._stored(t"/guilds/{self.id}/emojis", EmojiModel, StateCache.store_emojis, Emoji, self.id, cache=cache)

    async def fetch_emoji(self, emoji_id: SnowflakeLike, *, cache: bool = False) -> Emoji | NetworkError:
        """GET /guilds/{guild_id}/emojis/{emoji_id}."""
        parsed = parse(await self.client.get(t"/guilds/{self.id}/emojis/{emoji_id}", cache=cache), EmojiModel)
        return parsed if is_network_error(parsed) else Emoji(self.client, parsed, self.id)

    async def fetch_stickers(self, *, cache: bool = False) -> Generator[Sticker] | NetworkError:
        """GET /guilds/{guild_id}/stickers - the guild's own stickers."""
        return await self._stored(t"/guilds/{self.id}/stickers", StickerModel, StateCache.store_stickers, Sticker, cache=cache)

    async def fetch_invites(self, *, cache: bool = False) -> Generator[Invite] | NetworkError:
        """GET /guilds/{guild_id}/invites - every open invite to the guild; needs MANAGE_GUILD."""
        return self._entities(await self.client.get(t"/guilds/{self.id}/invites", cache=cache), InviteModel, Invite)

    async def fetch_voice_state(
        self,
        member: BaseMember | BaseUser | None = None,
        *,
        cache: bool = False,
    ) -> VoiceState | NetworkError:
        """GET /guilds/{guild_id}/voice-states/{user_id} - ``member``'s voice state here, or the bot's without one.

        Fails when they aren't connected to a voice channel of the guild.
        """
        route = t"/guilds/{self.id}/voice-states/@me" if member is None else t"/guilds/{self.id}/voice-states/{member.id}"
        return self._entity(await self.client.get(route, cache=cache), VoiceStateModel, VoiceState)

    async def fetch_welcome_screen(self, *, cache: bool = False) -> WelcomeScreen | NetworkError:
        """GET /guilds/{guild_id}/welcome-screen; needs MANAGE_GUILD unless the screen is enabled."""
        parsed = parse(await self.client.get(t"/guilds/{self.id}/welcome-screen", cache=cache), WelcomeScreenModel)
        return parsed if is_network_error(parsed) else WelcomeScreen(self.client, parsed, self.id)

    async def leave(self) -> NetworkError | None:
        """DELETE /users/@me/guilds/{guild_id} - remove the bot from the guild; fails for a guild it owns."""
        return no_content(await self.client.delete(t"/users/@me/guilds/{self.id}", json={}))

    def _members(self, result: RequestResult) -> Generator[Member] | NetworkError:
        """Return the failure in ``result``, or each member in its JSON array as a :class:`Member` of this guild."""
        if is_network_error(result):
            return result
        return (Member(self.client, GuildMember.model_validate(item), self.id) for item in result.json())


class Guild(Entity[GuildModel], BaseGuild):
    """A guild, as Discord returned it.

    Relations come in full when the guild's own data carries them (its roles, emojis and stickers); otherwise they're
    partial, to :meth:`~wd_discord.entities.base.Partial.fetch` when needed. :class:`GatewayGuild` carries more.
    """

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
    def description(self) -> str | None:
        """The guild's description, for a community guild."""
        return self.model.description

    @property
    def icon(self) -> ImageHash | None:
        """The guild's icon."""
        return self.model.icon

    @property
    def splash(self) -> ImageHash | None:
        """The guild's invite background."""
        return self.model.splash

    @property
    def banner(self) -> ImageHash | None:
        """The guild's banner."""
        return self.model.banner

    @property
    def owner(self) -> Member | PartialMember:
        """The guild's owner."""
        return self.get_member(self.model.owner_id) or self.member(self.model.owner_id)

    @property
    def afk_channel(self) -> Channel | PartialChannel | None:
        """The voice channel idle members are moved to, if the guild has one."""
        return self._channel(self.model.afk_channel_id)

    @property
    def afk_timeout(self) -> int:
        """The seconds a member idles in voice before they're moved to the AFK channel."""
        return self.model.afk_timeout

    @property
    def widget_channel(self) -> Channel | PartialChannel | None:
        """The channel the guild's widget invites to, if set."""
        return self._channel(self.model.widget_channel_id)

    @property
    def system_channel(self) -> Channel | PartialChannel | None:
        """The channel Discord posts join and boost messages in, if set."""
        return self._channel(self.model.system_channel_id)

    @property
    def rules_channel(self) -> Channel | PartialChannel | None:
        """A community guild's rules channel."""
        return self._channel(self.model.rules_channel_id)

    @property
    def public_updates_channel(self) -> Channel | PartialChannel | None:
        """The channel a community guild receives notices from Discord in."""
        return self._channel(self.model.public_updates_channel_id)

    @property
    def safety_alerts_channel(self) -> Channel | PartialChannel | None:
        """The channel a community guild receives safety alerts from Discord in."""
        return self._channel(self.model.safety_alerts_channel_id)

    @property
    @override
    def roles(self) -> Generator[Role]:
        """The guild's roles, ``@everyone`` included: as cached, else as this guild's data has them."""
        cached = super().roles
        return cached if cached is not None else (Role(self.client, role, self.id) for role in self.model.roles)

    @property
    def default_role(self) -> Role | PartialRole:
        """The ``@everyone`` role, which shares the guild's ID."""
        return self.get_role(self.id) or self.role(self.id)

    @override
    def get_role(self, role_id: SnowflakeLike) -> Role | None:
        """Return the role ``role_id``, as cached or else from this guild's data."""
        wanted = Snowflake.coerce(role_id)
        return super().get_role(wanted) or next((role for role in self.roles if role.id == wanted), None)

    @property
    @override
    def emojis(self) -> Generator[Emoji]:
        """The guild's custom emojis: as cached, else as this guild's data has them."""
        cached = super().emojis
        return cached if cached is not None else (Emoji(self.client, emoji, self.id) for emoji in self.model.emojis)

    @property
    @override
    def stickers(self) -> Generator[Sticker]:
        """The guild's own stickers: as cached, else as this guild's data has them."""
        cached = super().stickers
        if cached is not None:
            return cached
        return (Sticker(self.client, sticker) for sticker in self.model.stickers or [])

    @property
    def features(self) -> list[str]:
        """The guild's enabled features, such as ``COMMUNITY``."""
        return self.model.features

    @property
    def verification_level(self) -> VerificationLevel:
        """What a member must have done before they may talk."""
        return self.model.verification_level

    @property
    def mfa_level(self) -> MFALevel:
        """Whether moderators need two-factor authentication."""
        return self.model.mfa_level

    @property
    def nsfw_level(self) -> NSFWLevel:
        """The guild's age-restriction level."""
        return self.model.nsfw_level

    @property
    def premium_tier(self) -> PremiumTier:
        """The guild's boost level."""
        return self.model.premium_tier

    @property
    def premium_subscription_count(self) -> int | None:
        """How many boosts the guild has."""
        return self.model.premium_subscription_count

    @property
    def preferred_locale(self) -> str:
        """The language of a community guild, such as ``en-US``."""
        return self.model.preferred_locale

    @property
    def vanity_url_code(self) -> str | None:
        """The guild's vanity invite code, if it has one."""
        return self.model.vanity_url_code

    @property
    def max_members(self) -> int | None:
        """The most members the guild can hold."""
        return self.model.max_members

    @property
    def approximate_member_count(self) -> int | None:
        """Roughly how many members the guild has; only from :meth:`fetch` with ``with_counts``."""
        return self.model.approximate_member_count

    @property
    def approximate_presence_count(self) -> int | None:
        """Roughly how many members are online; only from :meth:`fetch` with ``with_counts``."""
        return self.model.approximate_presence_count

    @property
    def welcome_screen(self) -> WelcomeScreen | None:
        """A community guild's welcome screen, when Discord sent it along."""
        screen = self.model.welcome_screen
        return None if screen is None else WelcomeScreen(self.client, screen, self.id)

    def _channel(self, channel_id: Snowflake | None) -> Channel | PartialChannel | None:
        """Return the channel ``channel_id`` in full when the guild's data has it, else as a handle."""
        if channel_id is None:
            return None
        return self.get_channel(channel_id) or self.channel(channel_id)


class GatewayGuild(Guild):
    """A guild as GUILD_CREATE sent it: with its channels, threads, members and voice states.

    ``members`` holds everyone for a small guild, but only the bot (and members in voice) for a large one.
    """

    if TYPE_CHECKING:
        model: GuildCreate  # pyright: ignore[reportIncompatibleVariableOverride]

    @property
    @override
    def channels(self) -> Generator[Channel]:
        """The guild's channels, threads excluded: as cached, else as GUILD_CREATE sent them."""
        cached = super().channels
        if cached is not None:
            return cached
        return (Channel(self.client, channel.model_copy(update={"guild_id": self.id})) for channel in self.model.channels)

    @property
    @override
    def threads(self) -> Generator[Channel]:
        """The active threads the bot can see: as cached, else as GUILD_CREATE sent them."""
        cached = super().threads
        if cached is not None:
            return cached
        return (Channel(self.client, thread.model_copy(update={"guild_id": self.id})) for thread in self.model.threads)

    @property
    @override
    def members(self) -> Generator[Member]:
        """Every member when the client has them all, else the ones GUILD_CREATE sent; see the class docstring."""
        cached = super().members
        if cached is not None:
            return cached
        return (Member(self.client, member, self.id) for member in self.model.members if member.user is not None)

    @property
    @override
    def voice_states(self) -> Generator[VoiceState]:
        """Who is in which voice channel: as cached, else as GUILD_CREATE sent it."""
        cached = super().voice_states
        if cached is not None:
            return cached
        updated = (voice.model_copy(update={"guild_id": self.id}) for voice in self.model.voice_states)
        return (VoiceState(self.client, voice) for voice in updated)

    @property
    def member_count(self) -> int | None:
        """How many members the guild has."""
        return self.model.member_count

    @property
    def large(self) -> bool:
        """Whether the guild is past the gateway's large threshold, so ``members`` is incomplete."""
        return bool(self.model.large)

    @property
    def joined_at(self) -> str | None:
        """When the bot joined the guild, as an ISO 8601 timestamp."""
        return self.model.joined_at

    @override
    def get_member(self, user_id: SnowflakeLike) -> Member | None:
        """Return the member ``user_id`` as cached, or if GUILD_CREATE sent them along."""
        wanted = Snowflake.coerce(user_id)
        return super().get_member(wanted) or next((member for member in self.members if member.id == wanted), None)

    @override
    def get_channel(self, channel_id: SnowflakeLike) -> Channel | None:
        """Return the channel or thread ``channel_id`` as cached, or if GUILD_CREATE sent it."""
        wanted = Snowflake.coerce(channel_id)
        cached = super().get_channel(wanted)
        return cached or next((channel for channel in (*self.channels, *self.threads) if channel.id == wanted), None)


class PartialGuild(BaseGuild, Partial[Guild]):
    """A guild known only by ID."""


@dataclass(frozen=True)
class WelcomeScreen(Entity[WelcomeScreenModel]):
    """The screen a community guild shows new members: a description and up to 5 channels to start in."""

    guild_id: Snowflake
    """The guild the welcome screen belongs to."""

    @property
    def guild(self) -> PartialGuild:
        """The guild the welcome screen belongs to."""
        return PartialGuild(self.client, self.guild_id)

    @property
    def description(self) -> str | None:
        """The guild description shown on the screen."""
        return self.model.description

    @property
    def channels(self) -> Generator[WelcomeScreenChannel]:
        """The channels the screen suggests, in order."""
        for channel in self.model.welcome_channels:
            yield WelcomeScreenChannel(self.client, channel)


class WelcomeScreenChannel(Entity[WelcomeScreenChannelModel]):
    """One channel a welcome screen suggests."""

    @property
    def channel(self) -> PartialChannel:
        """The suggested channel."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def description(self) -> str:
        """What the screen says about the channel."""
        return self.model.description

    @property
    def emoji(self) -> PartialEmoji | None:
        """The emoji shown next to the channel, if any."""
        return self.model.emoji
