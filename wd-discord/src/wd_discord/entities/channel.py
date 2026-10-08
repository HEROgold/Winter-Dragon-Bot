"""Channels (https://docs.discord.com/developers/resources/channel)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.entities.base import ClientBound, Entity, Partial, parse
lazy from wd_discord.entities.message import Message
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.invite import Invite
lazy from wd_discord.responses import message_data


if TYPE_CHECKING:
    from collections.abc import Sequence

    from wd_core.client import JsonPayload

    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.permissions import ChannelType
    from wd_discord.snowflake import Snowflake


DEFAULT_INVITE_MAX_AGE = 86400
"""Seconds an invite made by :meth:`BaseChannel.create_invite` stays valid by default: 24 hours."""


class BaseChannel(ClientBound):
    """What can be done in a channel knowing only its ID: send messages, create invites, read it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The ID this object acts on."""

    @property
    def mention(self) -> str:
        """A clickable mention of the channel, as ``<#id>``."""
        return f"<#{self.id}>"

    async def fetch(self) -> Channel | NetworkError:
        """GET /channels/{channel_id}."""
        return self._entity(await self.client.get(f"/channels/{self.id}"), ChannelModel, Channel)

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
        return self._entity(await self.client.post(f"/channels/{self.id}/messages", json=payload), MessageModel, Message)

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


class Channel(Entity[ChannelModel], BaseChannel):
    """A channel, as Discord returned it."""

    @property
    @override
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


class PartialChannel(BaseChannel, Partial[Channel]):
    """A channel known only by ID."""
