"""Users (https://docs.discord.com/developers/resources/user)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import ClientBound, Entity, EntityStore, Partial
lazy from wd_discord.entities.channel import Channel
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.user import User as UserModel


if TYPE_CHECKING:
    from collections.abc import Sequence

    from wd_core.client import JsonPayload

    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.entities.message import Message
    from wd_discord.image import ImageHash
    from wd_discord.snowflake import Snowflake


class BaseUser(ClientBound):
    """What can be done to a user knowing only their ID: read them, open a DM, message them."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    @property
    def mention(self) -> str:
        """A clickable mention of the user, as ``<@id>``."""
        return f"<@{self.id}>"

    async def fetch(self) -> User | NetworkError:
        """GET /users/{user_id}."""
        return self._entity(await self.client.get(t"/users/{self.id}"), UserModel, User)

    async def dm(self) -> Channel | NetworkError:
        """POST /users/@me/channels - open the DM channel with this user, or return the one already open."""
        result = await self.client.post(t"/users/@me/channels", json={"recipient_id": str(self.id)})
        return self._entity(result, ChannelModel, Channel)

    async def send(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
    ) -> Message | NetworkError:
        """Send this user a direct message, opening the DM channel first.

        Fails, as a value, when the user doesn't accept DMs from the bot.
        """
        channel = await self.dm()
        if is_network_error(channel):
            return channel
        return await channel.send(content, embeds=embeds, components=components)


class User(Entity[UserModel], BaseUser):
    """A user, as Discord returned or sent them."""

    @property
    @override
    def id(self) -> Snowflake:
        """The user's ID."""
        return self.model.id

    @property
    def username(self) -> str:
        """The user's username; not unique across the platform."""
        return self.model.username

    @property
    def global_name(self) -> str | None:
        """The user's display name, if set."""
        return self.model.global_name

    @property
    def display_name(self) -> str:
        """The name Discord shows for the user: their display name, else their username."""
        return self.model.global_name or self.model.username

    @property
    def bot(self) -> bool:
        """Whether the user belongs to an application."""
        return bool(self.model.bot)


class CurrentUser(User):
    """The user behind the client's token."""

    async def edit(
        self,
        *,
        username: str | None = None,
        avatar: ImageHash | None = None,
        banner: ImageHash | None = None,
    ) -> CurrentUser | NetworkError:
        """PATCH /users/@me - change the username, avatar or banner; a ``None`` argument leaves it unchanged."""
        payload: JsonPayload = {}
        if username is not None:
            payload["username"] = username
        if avatar is not None:
            payload["avatar"] = str(avatar)
        if banner is not None:
            payload["banner"] = str(banner)
        return self._entity(await self.client.patch(t"/users/@me", json=payload), UserModel, CurrentUser)


class PartialUser(BaseUser, Partial[User]):
    """A user known only by ID."""


@dataclass(frozen=True)
class UserStore(EntityStore[PartialUser]):
    """Users the client can see."""

    async def me(self) -> CurrentUser | NetworkError:
        """GET /users/@me - the user behind the client's token."""
        return self._entity(await self.client.get(t"/users/@me"), UserModel, CurrentUser)
