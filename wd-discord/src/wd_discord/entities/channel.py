"""Channels (https://docs.discord.com/developers/resources/channel)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.invite import Invite
lazy from wd_discord.entities.member import PartialMember
lazy from wd_discord.entities.message import Message, PartialMessage
lazy from wd_discord.entities.role import BaseRole, PartialRole
lazy from wd_discord.entities.user import PartialUser, User
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.permissions import Permissions
lazy from wd_discord.resources.channel import Channel as ChannelModel
lazy from wd_discord.resources.channel import OverwriteParams, OverwriteType
lazy from wd_discord.resources.channel import PermissionOverwrite as PermissionOverwriteModel
lazy from wd_discord.resources.channel import ThreadMember as ThreadMemberModel
lazy from wd_discord.resources.invite import Invite as InviteModel
lazy from wd_discord.responses import message_data
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence
    from datetime import datetime

    from wd_core.client import JsonPayload

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.entities.member import BaseMember
    from wd_discord.entities.message import BaseMessage
    from wd_discord.entities.user import BaseUser
    from wd_discord.image import ImageHash
    from wd_discord.permissions import ChannelType
    from wd_discord.resources.channel import (
        ChannelParams,
        ForumTag,
        ThreadMetadata,
        VideoQualityMode,
    )
    from wd_discord.snowflake import SnowflakeLike


DEFAULT_INVITE_MAX_AGE = 86400
"""Seconds an invite made by :meth:`BaseChannel.create_invite` stays valid by default: 24 hours."""

type PermissionTarget = BaseRole | BaseMember | BaseUser
"""What a channel permission overwrite applies to: a role, or a member (their user works too)."""

MAX_MESSAGES_PER_PAGE = 100
"""The most messages ``GET /channels/{channel_id}/messages`` returns at once."""


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

    def message(self, message_id: SnowflakeLike) -> PartialMessage:
        """Return a handle on the message ``message_id`` in this channel, without fetching it."""
        return PartialMessage(self.client, Snowflake.coerce(message_id), self.id)

    async def fetch_messages(
        self,
        *,
        before: BaseMessage | None = None,
        after: BaseMessage | None = None,
        around: BaseMessage | None = None,
        limit: int = MAX_MESSAGES_PER_PAGE,
    ) -> Generator[Message] | NetworkError:
        """GET /channels/{channel_id}/messages - one page of messages, newest first; needs READ_MESSAGE_HISTORY.

        Pass at most one of ``before``, ``after`` or ``around`` to choose where the page starts; for the next page,
        pass the oldest message of this one as ``before``.
        """
        params = {"limit": str(limit)}
        for key, message in (("before", before), ("after", after), ("around", around)):
            if message is not None:
                params[key] = str(message.id)
        return self._entities(await self.client.get(t"/channels/{self.id}/messages", params=params), MessageModel, Message)

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

    async def delete_messages(
        self,
        messages: Iterable[BaseMessage],
        *,
        reason: AuditLogReason | str | None = None,
    ) -> NetworkError | None:
        """POST /channels/{channel_id}/messages/bulk-delete - delete 2 to 100 messages at once; needs MANAGE_MESSAGES.

        Messages older than 2 weeks can't be bulk deleted; Discord then fails the whole request.
        """
        payload: JsonPayload = {"messages": [str(message.id) for message in messages]}
        route = t"/channels/{self.id}/messages/bulk-delete"
        return no_content(await self.client.post(route, json=payload, headers=reason_headers(reason)))

    async def trigger_typing(self) -> NetworkError | None:
        """POST /channels/{channel_id}/typing - show the bot as typing for about 10 seconds, or until it sends."""
        return no_content(await self.client.post(t"/channels/{self.id}/typing", json={}))

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
        return self._entity(await self.client.post(t"/channels/{self.id}/invites", json=payload), InviteModel, Invite)

    async def fetch_invites(self) -> Generator[Invite] | NetworkError:
        """GET /channels/{channel_id}/invites - the channel's open invites; needs MANAGE_CHANNELS."""
        return self._entities(await self.client.get(t"/channels/{self.id}/invites"), InviteModel, Invite)

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
        target: PermissionTarget,
        *,
        allow: Permissions | None = None,
        deny: Permissions | None = None,
        reason: AuditLogReason | str | None = None,
    ) -> NetworkError | None:
        """PUT /channels/{channel_id}/permissions/{overwrite_id} - set ``target``'s overwrite on the channel.

        ``target`` is a role, or a member (or their user). Replaces its existing overwrite: whatever ``allow`` and
        ``deny`` leave out falls back to the role's or guild's permissions. Needs MANAGE_ROLES.
        """
        overwrite = OverwriteParams(
            id=target.id,
            type=OverwriteType.ROLE if isinstance(target, BaseRole) else OverwriteType.MEMBER,
            allow=allow or Permissions(0),
            deny=deny or Permissions(0),
        )
        route = t"/channels/{self.id}/permissions/{target.id}"
        return no_content(await self.client.put(route, json=overwrite.to_json(), headers=reason_headers(reason)))

    async def delete_permissions(
        self,
        target: PermissionTarget,
        *,
        reason: AuditLogReason | str | None = None,
    ) -> NetworkError | None:
        """DELETE /channels/{channel_id}/permissions/{overwrite_id} - remove a role's or member's overwrite."""
        route = t"/channels/{self.id}/permissions/{target.id}"
        return no_content(await self.client.delete(route, headers=reason_headers(reason)))

    async def join_thread(self) -> NetworkError | None:
        """PUT /channels/{channel_id}/thread-members/@me - add the bot to this thread."""
        return no_content(await self.client.put(t"/channels/{self.id}/thread-members/@me", json={}))

    async def leave_thread(self) -> NetworkError | None:
        """DELETE /channels/{channel_id}/thread-members/@me - remove the bot from this thread."""
        return no_content(await self.client.delete(t"/channels/{self.id}/thread-members/@me", json={}))

    async def add_thread_member(self, user: BaseUser | BaseMember) -> NetworkError | None:
        """PUT /channels/{channel_id}/thread-members/{user_id} - add someone to this thread; needs SEND_MESSAGES."""
        return no_content(await self.client.put(t"/channels/{self.id}/thread-members/{user.id}", json={}))

    async def remove_thread_member(self, user: BaseUser | BaseMember) -> NetworkError | None:
        """DELETE /channels/{channel_id}/thread-members/{user_id} - remove someone from this thread; needs MANAGE_THREADS."""
        return no_content(await self.client.delete(t"/channels/{self.id}/thread-members/{user.id}", json={}))


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
    def guild(self) -> PartialGuild | None:
        """The guild the channel belongs to; ``None`` for DM channels."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def parent(self) -> PartialChannel | None:
        """The category a guild channel sits in, or the channel a thread was started in."""
        parent_id = self.model.parent_id
        return None if parent_id is None else PartialChannel(self.client, parent_id)

    @property
    def position(self) -> int | None:
        """Where a guild channel sits in the channel list."""
        return self.model.position

    @property
    def topic(self) -> str | None:
        """The channel's topic, or a forum's guidelines."""
        return self.model.topic

    @property
    def nsfw(self) -> bool:
        """Whether the channel is age-restricted."""
        return bool(self.model.nsfw)

    @property
    def last_message(self) -> PartialMessage | None:
        """The latest message sent in the channel (or thread started, in a forum); it may have been deleted since."""
        message_id = self.model.last_message_id
        return None if message_id is None else PartialMessage(self.client, message_id, self.id)

    @property
    def bitrate(self) -> int | None:
        """A voice channel's bitrate, in bits per second."""
        return self.model.bitrate

    @property
    def user_limit(self) -> int | None:
        """How many users fit in a voice channel; ``0`` for no limit."""
        return self.model.user_limit

    @property
    def rate_limit_per_user(self) -> int | None:
        """Slowmode: the seconds a member waits between messages; ``0`` when off."""
        return self.model.rate_limit_per_user

    @property
    def rtc_region(self) -> str | None:
        """A voice channel's region; ``None`` picks automatically."""
        return self.model.rtc_region

    @property
    def video_quality_mode(self) -> VideoQualityMode | None:
        """A voice channel's camera video quality."""
        return self.model.video_quality_mode

    @property
    def recipients(self) -> Generator[User]:
        """The other users in a DM or group DM."""
        for user in self.model.recipients or []:
            yield User(self.client, user)

    @property
    def icon(self) -> ImageHash | None:
        """A group DM's icon."""
        return self.model.icon

    @property
    def owner(self) -> PartialUser | None:
        """Who created a group DM or thread."""
        owner_id = self.model.owner_id
        return None if owner_id is None else PartialUser(self.client, owner_id)

    @property
    def overwrites(self) -> Generator[PermissionOverwrite]:
        """The channel's permission overwrites; empty outside a guild."""
        guild_id = self.model.guild_id
        if guild_id is None:
            return
        for overwrite in self.model.permission_overwrites or []:
            yield PermissionOverwrite(self.client, overwrite, self.id, guild_id)

    @property
    def thread_metadata(self) -> ThreadMetadata | None:
        """A thread's archive and lock state."""
        return self.model.thread_metadata

    @property
    def thread_member(self) -> ThreadMember | None:
        """The bot's membership of this thread, when it joined it."""
        member = self.model.member
        return None if member is None else ThreadMember(self.client, member, self.id)

    @property
    def message_count(self) -> int | None:
        """How many messages a thread holds, deleted ones excluded."""
        return self.model.message_count

    @property
    def member_count(self) -> int | None:
        """Roughly how many users are in a thread; stops counting at 50."""
        return self.model.member_count

    @property
    def default_auto_archive_duration(self) -> int | None:
        """The minutes of inactivity before a new thread is archived."""
        return self.model.default_auto_archive_duration

    @property
    def available_tags(self) -> list[ForumTag]:
        """The tags a forum or media channel offers its posts."""
        return self.model.available_tags or []

    @property
    def applied_tags(self) -> list[Snowflake]:
        """The IDs of the parent forum's tags applied to this post."""
        return self.model.applied_tags or []

    @property
    def permissions(self) -> Permissions | None:
        """The invoking user's permissions in the channel, overwrites included.

        Only known for a channel resolved from an interaction option; ``None`` everywhere else.
        """
        return self.model.permissions

    @property
    def app_permissions(self) -> Permissions | None:
        """The bot's permissions in the channel, overwrites included.

        Only known for an interaction's channel; ``None`` everywhere else.
        """
        return self.model.app_permissions


class PartialChannel(BaseChannel, Partial[Channel]):
    """A channel known only by ID."""


@dataclass(frozen=True)
class PermissionOverwrite(Entity[PermissionOverwriteModel]):
    """One role's or member's permission overwrite on a guild channel."""

    channel_id: Snowflake
    """The channel the overwrite is set on."""
    guild_id: Snowflake
    """The guild the channel belongs to."""

    @property
    def id(self) -> Snowflake:
        """The ID of the role or member the overwrite applies to."""
        return self.model.id

    @property
    def type(self) -> OverwriteType:
        """Whether the overwrite applies to a role or a member."""
        return self.model.type

    @property
    def target(self) -> PartialRole | PartialMember:
        """The role or member the overwrite applies to."""
        if self.model.type is OverwriteType.ROLE:
            return PartialRole(self.client, self.model.id, self.guild_id)
        return PartialMember(self.client, self.model.id, self.guild_id)

    @property
    def channel(self) -> PartialChannel:
        """The channel the overwrite is set on."""
        return PartialChannel(self.client, self.channel_id)

    @property
    def allow(self) -> Permissions:
        """The permissions the overwrite grants."""
        return self.model.allow

    @property
    def deny(self) -> Permissions:
        """The permissions the overwrite takes away."""
        return self.model.deny

    async def delete(self, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /channels/{channel_id}/permissions/{overwrite_id}; needs MANAGE_ROLES."""
        route = t"/channels/{self.channel_id}/permissions/{self.id}"
        return no_content(await self.client.delete(route, headers=reason_headers(reason)))


@dataclass(frozen=True)
class ThreadMember(Entity[ThreadMemberModel]):
    """A user's membership of a thread."""

    thread_id: Snowflake
    """The thread the membership is for; Discord leaves it out of some payloads."""

    @property
    def thread(self) -> PartialChannel:
        """The thread the membership is for."""
        return PartialChannel(self.client, self.model.id or self.thread_id)

    @property
    def user(self) -> PartialUser | None:
        """The member of the thread; Discord leaves it out of some payloads."""
        user_id = self.model.user_id
        return None if user_id is None else PartialUser(self.client, user_id)

    @property
    def joined_at(self) -> datetime:
        """When the user last joined the thread."""
        return self.model.join_timestamp

    @property
    def flags(self) -> int:
        """The user's notification settings for the thread."""
        return self.model.flags
