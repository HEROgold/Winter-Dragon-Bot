"""Channels (https://docs.discord.com/developers/resources/channel)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content, parse
lazy from wd_discord.entities.message import Message
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.invite import Invite
lazy from wd_discord.responses import message_data


if TYPE_CHECKING:
    from collections.abc import Sequence

    from wd_core.client import JsonPayload

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.permissions import ChannelType
    from wd_discord.resources.channel import ChannelParams, OverwriteParams
    from wd_discord.snowflake import Snowflake, SnowflakeLike


DEFAULT_INVITE_MAX_AGE = 86400
"""Seconds an invite made by :meth:`BaseChannel.create_invite` stays valid by default: 24 hours."""


class BaseChannel(ClientBound):
    """What can be done in a channel knowing only its ID: read, edit or delete it, send messages, set permissions."""

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
        return self._entity(await self.client.get(t"/channels/{self.id}"), ChannelModel, Channel)

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
        return self._entity(await self.client.post(t"/channels/{self.id}/messages", json=payload), MessageModel, Message)

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
        return parse(await self.client.post(t"/channels/{self.id}/invites", json=payload), Invite)

    async def edit(self, params: ChannelParams, *, reason: AuditLogReason | str | None = None) -> Channel | NetworkError:
        """PATCH /channels/{channel_id} - change the settings set in ``params``; needs MANAGE_CHANNELS.

        Renaming a channel is rate limited to twice per 10 minutes.
        """
        result = await self.client.patch(t"/channels/{self.id}", json=params.to_json(), headers=reason_headers(reason))
        return self._entity(result, ChannelModel, Channel)

    async def delete(self, *, reason: AuditLogReason | str | None = None) -> Channel | NetworkError:
        """DELETE /channels/{channel_id} - delete the channel, or close a DM; returns the deleted channel.

        Deleting a category leaves its channels in place, outside any category.
        """
        return self._entity(
            await self.client.delete(t"/channels/{self.id}", headers=reason_headers(reason)),
            ChannelModel,
            Channel,
        )

    async def set_permissions(
        self,
        overwrite: OverwriteParams,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> NetworkError | None:
        """PUT /channels/{channel_id}/permissions/{overwrite_id} - set one role's or member's overwrite on the channel.

        Replaces that role's or member's existing overwrite; needs MANAGE_ROLES.
        """
        route = t"/channels/{self.id}/permissions/{overwrite.id}"
        return no_content(await self.client.put(route, json=overwrite.to_json(), headers=reason_headers(reason)))

    async def delete_permissions(
        self,
        target_id: SnowflakeLike,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> NetworkError | None:
        """DELETE /channels/{channel_id}/permissions/{overwrite_id} - remove a role's or member's overwrite."""
        route = t"/channels/{self.id}/permissions/{target_id}"
        return no_content(await self.client.delete(route, headers=reason_headers(reason)))


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

    @property
    def parent_id(self) -> Snowflake | None:
        """The category a guild channel sits in, or the channel a thread was started in."""
        return self.model.parent_id


class PartialChannel(BaseChannel, Partial[Channel]):
    """A channel known only by ID."""
