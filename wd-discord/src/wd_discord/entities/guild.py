"""Guilds (https://docs.discord.com/developers/resources/guild)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content, parse
lazy from wd_discord.entities.channel import Channel, PartialChannel
lazy from wd_discord.entities.emoji import Emoji, Sticker
lazy from wd_discord.entities.invite import Invite
lazy from wd_discord.entities.member import Member, PartialMember
lazy from wd_discord.entities.role import PartialRole, Role
lazy from wd_discord.entities.voice import VoiceState
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
    from collections.abc import Generator

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError, RequestResult
    from wd_discord.entities.member import BaseMember
    from wd_discord.entities.user import BaseUser
    from wd_discord.gateway.events import GuildCreate
    from wd_discord.image import ImageHash
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
"""The most members ``GET /guilds/{guild_id}/members`` returns at once."""


class BaseGuild(ClientBound):
    """What can be done to a guild knowing only its ID: read it, its channels, members, roles and expressions."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    async def fetch(self, *, with_counts: bool = False) -> Guild | NetworkError:
        """GET /guilds/{guild_id}; ``with_counts`` fills in the approximate member and online counts."""
        params = {"with_counts": "true"} if with_counts else {}
        return self._entity(await self.client.get(t"/guilds/{self.id}", params=params), GuildModel, Guild)

    def channel(self, channel_id: SnowflakeLike) -> PartialChannel:
        """Return a handle on the channel ``channel_id``, without fetching it."""
        return PartialChannel(self.client, Snowflake.coerce(channel_id))

    async def fetch_channels(self) -> Generator[Channel] | NetworkError:
        """GET /guilds/{guild_id}/channels - the guild's channels, threads excluded."""
        return self._entities(await self.client.get(t"/guilds/{self.id}/channels"), ChannelModel, Channel)

    async def create_channel(
        self,
        params: GuildChannelParams,
        *,
        reason: AuditLogReason | str | None = None,
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
    ) -> Generator[Member] | NetworkError:
        """GET /guilds/{guild_id}/members - one page of members, by user ID, after the member ``after``.

        Pass the last member of a page as ``after`` to get the next one; a page shorter than ``limit`` is the last.
        Needs the GUILD_MEMBERS intent.
        """
        params = {"limit": str(limit), "after": "0" if after is None else str(after.id)}
        return self._members(await self.client.get(t"/guilds/{self.id}/members", params=params))

    async def search_members(self, query: str, *, limit: int = 1) -> Generator[Member] | NetworkError:
        """GET /guilds/{guild_id}/members/search - the members whose username or nickname starts with ``query``."""
        params = {"query": query, "limit": str(limit)}
        return self._members(await self.client.get(t"/guilds/{self.id}/members/search", params=params))

    def role(self, role_id: SnowflakeLike) -> PartialRole:
        """Return a handle on the role ``role_id`` of this guild, without fetching it."""
        return PartialRole(self.client, Snowflake.coerce(role_id), self.id)

    async def fetch_roles(self) -> Generator[Role] | NetworkError:
        """GET /guilds/{guild_id}/roles - every role of the guild."""
        result = await self.client.get(t"/guilds/{self.id}/roles")
        if is_network_error(result):
            return result
        return (Role(self.client, RoleModel.model_validate(item), self.id) for item in result.json())

    async def fetch_emojis(self) -> Generator[Emoji] | NetworkError:
        """GET /guilds/{guild_id}/emojis - the guild's custom emojis."""
        result = await self.client.get(t"/guilds/{self.id}/emojis")
        if is_network_error(result):
            return result
        return (Emoji(self.client, EmojiModel.model_validate(item), self.id) for item in result.json())

    async def fetch_emoji(self, emoji_id: SnowflakeLike) -> Emoji | NetworkError:
        """GET /guilds/{guild_id}/emojis/{emoji_id}."""
        parsed = parse(await self.client.get(t"/guilds/{self.id}/emojis/{emoji_id}"), EmojiModel)
        return parsed if is_network_error(parsed) else Emoji(self.client, parsed, self.id)

    async def fetch_stickers(self) -> Generator[Sticker] | NetworkError:
        """GET /guilds/{guild_id}/stickers - the guild's own stickers."""
        return self._entities(await self.client.get(t"/guilds/{self.id}/stickers"), StickerModel, Sticker)

    async def fetch_invites(self) -> Generator[Invite] | NetworkError:
        """GET /guilds/{guild_id}/invites - every open invite to the guild; needs MANAGE_GUILD."""
        return self._entities(await self.client.get(t"/guilds/{self.id}/invites"), InviteModel, Invite)

    async def fetch_voice_state(self, member: BaseMember | BaseUser | None = None) -> VoiceState | NetworkError:
        """GET /guilds/{guild_id}/voice-states/{user_id} - ``member``'s voice state here, or the bot's without one.

        Fails when they aren't connected to a voice channel of the guild.
        """
        route = t"/guilds/{self.id}/voice-states/@me" if member is None else t"/guilds/{self.id}/voice-states/{member.id}"
        return self._entity(await self.client.get(route), VoiceStateModel, VoiceState)

    async def fetch_welcome_screen(self) -> WelcomeScreen | NetworkError:
        """GET /guilds/{guild_id}/welcome-screen; needs MANAGE_GUILD unless the screen is enabled."""
        parsed = parse(await self.client.get(t"/guilds/{self.id}/welcome-screen"), WelcomeScreenModel)
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
    def roles(self) -> Generator[Role]:
        """The guild's roles, ``@everyone`` included."""
        for role in self.model.roles:
            yield Role(self.client, role, self.id)

    @property
    def default_role(self) -> Role | PartialRole:
        """The ``@everyone`` role, which shares the guild's ID."""
        return self.get_role(self.id) or self.role(self.id)

    def get_role(self, role_id: SnowflakeLike) -> Role | None:
        """Return the role ``role_id`` from the guild's data, without a request; ``None`` if it isn't one of them."""
        wanted = Snowflake.coerce(role_id)
        return next((role for role in self.roles if role.id == wanted), None)

    def get_member(self, user_id: SnowflakeLike) -> Member | None:  # noqa: ARG002 - GatewayGuild knows members
        """Return the member ``user_id`` from the guild's data, without a request; a fetched guild has none."""
        return None

    def get_channel(self, channel_id: SnowflakeLike) -> Channel | None:  # noqa: ARG002 - GatewayGuild knows channels
        """Return the channel ``channel_id`` from the guild's data, without a request; a fetched guild has none."""
        return None

    @property
    def emojis(self) -> Generator[Emoji]:
        """The guild's custom emojis."""
        for emoji in self.model.emojis:
            yield Emoji(self.client, emoji, self.id)

    @property
    def stickers(self) -> Generator[Sticker]:
        """The guild's own stickers."""
        for sticker in self.model.stickers or []:
            yield Sticker(self.client, sticker)

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
    def channels(self) -> Generator[Channel]:
        """The guild's channels, threads excluded."""
        for channel in self.model.channels:
            yield Channel(self.client, channel.model_copy(update={"guild_id": self.id}))

    @property
    def threads(self) -> Generator[Channel]:
        """The active threads the bot can see."""
        for thread in self.model.threads:
            yield Channel(self.client, thread.model_copy(update={"guild_id": self.id}))

    @property
    def members(self) -> Generator[Member]:
        """The members Discord sent along; see the class docstring for which."""
        for member in self.model.members:
            if member.user is not None:
                yield Member(self.client, member, self.id)

    @property
    def voice_states(self) -> Generator[VoiceState]:
        """Who is in which of the guild's voice channels."""
        for state in self.model.voice_states:
            yield VoiceState(self.client, state.model_copy(update={"guild_id": self.id}))

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
        """Return the member ``user_id`` if Discord sent them along, without a request."""
        wanted = Snowflake.coerce(user_id)
        return next((member for member in self.members if member.id == wanted), None)

    @override
    def get_channel(self, channel_id: SnowflakeLike) -> Channel | None:
        """Return the channel or thread ``channel_id`` of the guild, without a request."""
        wanted = Snowflake.coerce(channel_id)
        return next((channel for channel in (*self.channels, *self.threads) if channel.id == wanted), None)


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
