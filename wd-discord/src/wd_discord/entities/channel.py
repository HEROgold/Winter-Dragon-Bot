"""Channels (https://docs.discord.com/developers/resources/channel)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity, Store, parse
lazy from wd_discord.entities.message import Message
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.invite import Invite
lazy from wd_discord.responses import message_data
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Sequence

    from wd_core.client import JsonPayload

    from wd_discord.client import Client, NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.permissions import ChannelType
    from wd_discord.snowflake import SnowflakeLike


DEFAULT_INVITE_MAX_AGE = 86400
"""Seconds an invite made by :meth:`BaseChannel.create_invite` stays valid by default: 24 hours."""


class BaseChannel(ABC):
    """What can be done in a channel knowing only its ID: send messages, create invites, read it."""

    client: Client

    @property
    @abstractmethod
    def id(self) -> Snowflake:
        """The channel's ID."""

    @property
    def mention(self) -> str:
        """A clickable mention of the channel, as ``<#id>``."""
        return f"<#{self.id}>"

    async def fetch(self) -> Channel | NetworkError:
        """GET /channels/{channel_id}."""
        channel = parse(await self.client.get(f"/channels/{self.id}"), ChannelModel)
        return channel if is_network_error(channel) else Channel(self.client, channel)

    async def send(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
    ) -> Message | NetworkError:
        """POST /channels/{channel_id}/messages - send a message; DM channels included.

        Discord needs at least one of ``content``, ``embeds`` or ``components``.
        """
        payload = message_data(content=content, embeds=embeds, components=components)
        message = parse(await self.client.post(f"/channels/{self.id}/messages", json=payload), MessageModel)
        return message if is_network_error(message) else Message(self.client, message)

    async def create_invite(
        self,
        *,
        max_age: int = DEFAULT_INVITE_MAX_AGE,
        max_uses: int = 1,
        temporary: bool = False,
        unique: bool = True,
    ) -> Invite | NetworkError:
        """POST /channels/{channel_id}/invites - create an invite to this channel.

        Defaults to a single-use 24-hour invite, meant for handing to one specific person.
        """
        payload: JsonPayload = {"max_age": max_age, "max_uses": max_uses, "temporary": temporary, "unique": unique}
        return parse(await self.client.post(f"/channels/{self.id}/invites", json=payload), Invite)


@dataclass(frozen=True)
class PartialChannel(BaseChannel):
    """A channel known only by ID."""

    client: Client
    channel_id: Snowflake

    @property
    def id(self) -> Snowflake:
        """The channel's ID."""
        return self.channel_id


class Channel(Entity[ChannelModel], BaseChannel):
    """A channel, as Discord returned it."""

    @property
    def id(self) -> Snowflake:
        """The channel's ID."""
        return self.model.id

    @property
    def name(self) -> str | None:
        """The channel's name; ``None`` for DM channels."""
        return self.model.name

    @property
    def type(self) -> ChannelType:
        """The kind of channel."""
        return self.model.type

    @property
    def guild_id(self) -> Snowflake | None:
        """The guild the channel belongs to; ``None`` for DM channels."""
        return self.model.guild_id


@dataclass(frozen=True)
class ChannelStore(Store):
    """Channels the client can see."""

    def partial(self, channel_id: SnowflakeLike) -> PartialChannel:
        """Return a handle on the channel ``channel_id``, without fetching it."""
        return PartialChannel(self.client, Snowflake.coerce(channel_id))

    async def fetch(self, channel_id: SnowflakeLike) -> Channel | NetworkError:
        """GET /channels/{channel_id}."""
        return await self.partial(channel_id).fetch()
