"""Asking Discord what a user, channel, role or guild is called, through a REST-only bot client with a short cache.

A lookup that succeeded or found nothing is kept for :data:`CACHE_LIFETIME`. One that couldn't be answered (a rate
limit, an outage, a missing permission) is never kept, so the next page load asks again.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
lazy import asyncio
lazy from typing import TYPE_CHECKING, Self

lazy from wd_discord import Client, Token, is_network_error
lazy from wd_discord.log import get_logger
lazy from wd_discord.snowflake import Snowflake
lazy from wd_types.clock import utc_now

lazy from winter_dragon.web.references import LookupStatus, Named


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from types import TracebackType

    from wd_discord import Channel, Guild, Role, User
    from wd_discord.client import NetworkError
    from wd_discord.entities.user import UserGuild


CACHE_LIFETIME = timedelta(minutes=5)
"""How long a found, or not found, entity is remembered."""

logger = get_logger(__name__)


@dataclass(frozen=True)
class Fetched[T]:
    """The outcome of fetching one entity: its status, and the entity itself when found."""

    status: LookupStatus
    entity: T | None = None

    @classmethod
    def failed(cls, error: NetworkError) -> Self:
        """Return the outcome for a request that failed: unknown when Discord has no such thing, else unavailable."""
        unknown = getattr(error, "unknown_resource", False)  # only an API error can say the thing doesn't exist
        return cls(LookupStatus.UNKNOWN if unknown else LookupStatus.UNAVAILABLE)


def named_user(fetched: Fetched[User]) -> Named:
    """Return what a user's name and picture are, for a reference link."""
    if fetched.entity is None:
        return Named(fetched.status)
    user = fetched.entity
    avatar = None if user.model.avatar is None else user.model.avatar.url(f"avatars/{user.id}")
    return Named(fetched.status, user.display_name, avatar)


def named_channel(fetched: Fetched[Channel]) -> Named:
    """Return what a channel is called and which guild it is in, for a reference link."""
    if fetched.entity is None:
        return Named(fetched.status)
    channel = fetched.entity
    guild = channel.guild
    return Named(fetched.status, channel.name or str(channel.id), guild_id=None if guild is None else guild.id)


def named_role(fetched: Fetched[Role]) -> Named:
    """Return what a role is called and which guild it is in, for a reference link."""
    if fetched.entity is None:
        return Named(fetched.status)
    return Named(fetched.status, fetched.entity.name, guild_id=fetched.entity.guild_id)


def named_guild(fetched: Fetched[Guild]) -> Named:
    """Return what a guild is called and its icon, for a reference link."""
    if fetched.entity is None:
        return Named(fetched.status)
    guild = fetched.entity
    icon = None if guild.icon is None else guild.icon.url(f"icons/{guild.id}")
    return Named(fetched.status, guild.name, icon)


class DiscordLookup:
    """The bot's REST client, and the names it has fetched; open it with ``async with`` before use."""

    def __init__(self, token: str, *, lifetime: timedelta = CACHE_LIFETIME, now: Callable[[], datetime] | None = None) -> None:
        """Ask Discord with the bot ``token``; remember answers for ``lifetime``, as read from the clock ``now``."""
        self._token = token
        self._lifetime = lifetime
        self._now = utc_now if now is None else now
        self._client: Client | None = None
        self._kept: dict[tuple[str, Snowflake, Snowflake | None], tuple[datetime, Fetched[object]]] = {}

    async def __aenter__(self) -> Self:
        """Open the client."""
        self._client = Client(Token(self._token))
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client."""
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, traceback)
            self._client = None

    @property
    def client(self) -> Client:
        """The open client; raises when the lookup wasn't opened."""
        if self._client is None:
            message = "Open the DiscordLookup with `async with` before asking it for names."
            raise RuntimeError(message)
        return self._client

    async def user(self, user_id: Snowflake) -> Fetched[User]:
        """Fetch a user."""
        return await self._fetched("user", user_id, None, lambda: self.client.users.fetch(user_id))

    async def channel(self, channel_id: Snowflake) -> Fetched[Channel]:
        """Fetch a channel."""
        return await self._fetched("channel", channel_id, None, lambda: self.client.channels.fetch(channel_id))

    async def guild(self, guild_id: Snowflake) -> Fetched[Guild]:
        """Fetch a guild, with its member counts."""
        guild = self.client.guilds.partial(guild_id)
        return await self._fetched("guild", guild_id, None, lambda: guild.fetch(with_counts=True))

    async def role(self, guild_id: Snowflake, role_id: Snowflake) -> Fetched[Role]:
        """Fetch a role of a guild."""

        async def fetch() -> Role | NetworkError:
            roles = await self.client.guilds.partial(guild_id).fetch_roles()
            if is_network_error(roles):
                return roles
            return next((role for role in roles if role.id == role_id), None) or _no_such_role()

        return await self._fetched("role", role_id, guild_id, fetch)

    async def bot_guild_ids(self) -> frozenset[Snowflake] | None:
        """Return the IDs of every guild the bot is in, kept like any lookup; ``None`` when Discord couldn't say."""
        fetched = await self._fetched("bot guilds", Snowflake(0), None, self._bot_guilds)
        return None if fetched.entity is None else frozenset(guild.id for guild in fetched.entity)

    async def _bot_guilds(self) -> list[UserGuild] | NetworkError:
        """Fetch every guild the bot is in."""
        guilds = await self.client.users.guilds()
        return guilds if is_network_error(guilds) else list(guilds)

    async def users(self, ids: Iterable[Snowflake]) -> dict[Snowflake, Named]:
        """Return what Discord says about each of the users ``ids``, asking for them together."""
        wanted = tuple(dict.fromkeys(ids))
        found = await asyncio.gather(*(self.user(user_id) for user_id in wanted))
        return {user_id: named_user(fetched) for user_id, fetched in zip(wanted, found, strict=True)}

    async def _fetched[T](
        self,
        kind: str,
        entity_id: Snowflake,
        guild_id: Snowflake | None,
        fetch: Callable[[], Awaitable[T | NetworkError]],
    ) -> Fetched[T]:
        """Return the cached outcome for the entity, or fetch it; keep it unless Discord couldn't answer."""
        key = (kind, entity_id, guild_id)
        now = self._now()
        if (kept := self._kept.get(key)) is not None and kept[0] > now:
            return kept[1]  # pyrefly: ignore[bad-return] - the key's kind decides the entity's type
        result = await fetch()
        if is_network_error(result):
            outcome: Fetched[T] = Fetched.failed(result)
            if outcome.status is LookupStatus.UNAVAILABLE:
                logger.warning(t"Couldn't look up {kind} {entity_id} on Discord: {result}")
        else:
            outcome = Fetched(LookupStatus.FOUND, result)
        if outcome.status is not LookupStatus.UNAVAILABLE:
            self._kept[key] = (now + self._lifetime, outcome)
        return outcome


def _no_such_role() -> NetworkError:
    """Return the failure for a role that its guild doesn't have."""
    from wd_discord.errors.api import ApiResponseError  # noqa: PLC0415

    return ApiResponseError(code=10011, message="Unknown Role", status=404)
