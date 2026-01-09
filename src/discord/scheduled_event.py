"""The MIT License (MIT).

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union, overload

from .asset import Asset
from .channel import StageChannel, VoiceChannel
from .enums import EntityType, EventStatus, PrivacyLevel, try_enum
from .mixins import Hashable
from .object import OLDEST_OBJECT, Object
from .utils import MISSING, _bytes_to_base64_data, _get_as_snowflake, parse_time


if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import datetime

    from .abc import Snowflake
    from .guild import Guild
    from .state import ConnectionState
    from .types.scheduled_event import (
        EntityMetadata,
    )
    from .types.scheduled_event import (
        GuildScheduledEvent as BaseGuildScheduledEventPayload,
    )
    from .types.scheduled_event import (
        GuildScheduledEventWithUserCount as GuildScheduledEventWithUserCountPayload,
    )
    from .user import User

    GuildScheduledEventPayload = Union[BaseGuildScheduledEventPayload, GuildScheduledEventWithUserCountPayload]

# fmt: off
__all__ = (
    "ScheduledEvent",
)
# fmt: on


class ScheduledEvent(Hashable):
    """Represents a scheduled event in a guild.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: x == y

            Checks if two scheduled events are equal.

        .. describe:: x != y

            Checks if two scheduled events are not equal.

        .. describe:: hash(x)

            Returns the scheduled event's hash.

    Attributes
    ----------
    id: :class:`int`
        The scheduled event's ID.
    name: :class:`str`
        The name of the scheduled event.
    description: Optional[:class:`str`]
        The description of the scheduled event.
    entity_type: :class:`EntityType`
        The type of entity this event is for.
    entity_id: Optional[:class:`int`]
        The ID of the entity this event is for if available.
    start_time: :class:`datetime.datetime`
        The time that the scheduled event will start in UTC.
    end_time: Optional[:class:`datetime.datetime`]
        The time that the scheduled event will end in UTC.
    privacy_level: :class:`PrivacyLevel`
        The privacy level of the scheduled event.
    status: :class:`EventStatus`
        The status of the scheduled event.
    user_count: :class:`int`
        The number of users subscribed to the scheduled event.
    creator: Optional[:class:`User`]
        The user that created the scheduled event.
    creator_id: Optional[:class:`int`]
        The ID of the user that created the scheduled event.

        .. versionadded:: 2.2
    location: Optional[:class:`str`]
        The location of the scheduled event.

    """

    __slots__ = (
        "_cover_image",
        "_state",
        "_users",
        "channel_id",
        "creator",
        "creator_id",
        "description",
        "end_time",
        "entity_id",
        "entity_type",
        "guild_id",
        "id",
        "location",
        "name",
        "privacy_level",
        "start_time",
        "status",
        "user_count",
    )

    def __init__(self, *, state: ConnectionState, data: GuildScheduledEventPayload) -> None:
        self._state = state
        self._users: dict[int, User] = {}
        self._update(data)

    def _update(self, data: GuildScheduledEventPayload) -> None:
        self.id: int = int(data["id"])
        self.guild_id: int = int(data["guild_id"])
        self.name: str = data["name"]
        self.description: str | None = data.get("description")
        self.entity_type: EntityType = try_enum(EntityType, data["entity_type"])
        self.entity_id: int | None = _get_as_snowflake(data, "entity_id")
        self.start_time: datetime = parse_time(data["scheduled_start_time"])
        self.privacy_level: PrivacyLevel = try_enum(PrivacyLevel, data["status"])
        self.status: EventStatus = try_enum(EventStatus, data["status"])
        self._cover_image: str | None = data.get("image", None)
        self.user_count: int = data.get("user_count", 0)
        self.creator_id: int | None = _get_as_snowflake(data, "creator_id")

        creator = data.get("creator")
        self.creator: User | None = self._state.store_user(creator) if creator else None

        if self.creator_id is not None and self.creator is None:
            self.creator = self._state.get_user(self.creator_id)

        self.end_time: datetime | None = parse_time(data.get("scheduled_end_time"))
        self.channel_id: int | None = _get_as_snowflake(data, "channel_id")

        metadata = data.get("entity_metadata")
        self._unroll_metadata(metadata)

    def _unroll_metadata(self, data: EntityMetadata | None) -> None:
        self.location: str | None = data.get("location") if data else None

    def __repr__(self) -> str:
        return f"<GuildScheduledEvent id={self.id} name={self.name!r} guild_id={self.guild_id!r} creator={self.creator!r}>"

    @property
    def cover_image(self) -> Asset | None:
        """Optional[:class:`Asset`]: The scheduled event's cover image."""
        if self._cover_image is None:
            return None
        return Asset._from_scheduled_event_cover_image(self._state, self.id, self._cover_image)

    @property
    def guild(self) -> Guild | None:
        """Optional[:class:`Guild`]: The guild this scheduled event is in."""
        return self._state._get_guild(self.guild_id)

    @property
    def channel(self) -> VoiceChannel | StageChannel | None:
        """Optional[Union[:class:`VoiceChannel`, :class:`StageChannel`]]: The channel this scheduled event is in."""
        return self.guild.get_channel(self.channel_id)  # type: ignore

    @property
    def url(self) -> str:
        """:class:`str`: The url for the scheduled event."""
        return f"https://discord.com/events/{self.guild_id}/{self.id}"

    async def __modify_status(self, status: EventStatus, reason: str | None, /) -> ScheduledEvent:
        payload = {"status": status.value}
        data = await self._state.http.edit_scheduled_event(self.guild_id, self.id, **payload, reason=reason)
        s = ScheduledEvent(state=self._state, data=data)
        s._users = self._users
        return s

    async def start(self, *, reason: str | None = None) -> ScheduledEvent:
        """|coro|.

        Starts the scheduled event.

        Shorthand for:

        .. code-block:: python3

            await event.edit(status=EventStatus.active)

        Parameters
        ----------
        reason: Optional[:class:`str`]
            The reason for starting the scheduled event.

        Raises
        ------
        ValueError
            The scheduled event has already started or has ended.
        Forbidden
            You do not have the proper permissions to start the scheduled event.
        HTTPException
            The scheduled event could not be started.

        Returns
        -------
        :class:`ScheduledEvent`
            The scheduled event that was started.

        """
        if self.status is not EventStatus.scheduled:
            msg = "This scheduled event is already running."
            raise ValueError(msg)

        return await self.__modify_status(EventStatus.active, reason)

    async def end(self, *, reason: str | None = None) -> ScheduledEvent:
        """|coro|.

        Ends the scheduled event.

        Shorthand for:

        .. code-block:: python3

            await event.edit(status=EventStatus.completed)

        Parameters
        ----------
        reason: Optional[:class:`str`]
            The reason for ending the scheduled event.

        Raises
        ------
        ValueError
            The scheduled event is not active or has already ended.
        Forbidden
            You do not have the proper permissions to end the scheduled event.
        HTTPException
            The scheduled event could not be ended.

        Returns
        -------
        :class:`ScheduledEvent`
            The scheduled event that was ended.

        """
        if self.status is not EventStatus.active:
            msg = "This scheduled event is not active."
            raise ValueError(msg)

        return await self.__modify_status(EventStatus.ended, reason)

    async def cancel(self, *, reason: str | None = None) -> ScheduledEvent:
        """|coro|.

        Cancels the scheduled event.

        Shorthand for:

        .. code-block:: python3

            await event.edit(status=EventStatus.cancelled)

        Parameters
        ----------
        reason: Optional[:class:`str`]
            The reason for cancelling the scheduled event.

        Raises
        ------
        ValueError
            The scheduled event is already running.
        Forbidden
            You do not have the proper permissions to cancel the scheduled event.
        HTTPException
            The scheduled event could not be cancelled.

        Returns
        -------
        :class:`ScheduledEvent`
            The scheduled event that was cancelled.

        """
        if self.status is not EventStatus.scheduled:
            msg = "This scheduled event is already running."
            raise ValueError(msg)

        return await self.__modify_status(EventStatus.cancelled, reason)

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        description: str = ...,
        start_time: datetime = ...,
        end_time: datetime | None = ...,
        privacy_level: PrivacyLevel = ...,
        status: EventStatus = ...,
        image: bytes = ...,
        reason: str | None = ...,
    ) -> ScheduledEvent: ...

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        description: str = ...,
        channel: Snowflake,
        start_time: datetime = ...,
        end_time: datetime | None = ...,
        privacy_level: PrivacyLevel = ...,
        entity_type: Literal[EntityType.voice, EntityType.stage_instance],
        status: EventStatus = ...,
        image: bytes = ...,
        reason: str | None = ...,
    ) -> ScheduledEvent: ...

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        description: str = ...,
        start_time: datetime = ...,
        end_time: datetime = ...,
        privacy_level: PrivacyLevel = ...,
        entity_type: Literal[EntityType.external],
        status: EventStatus = ...,
        image: bytes = ...,
        location: str,
        reason: str | None = ...,
    ) -> ScheduledEvent: ...

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        description: str = ...,
        channel: VoiceChannel | StageChannel,
        start_time: datetime = ...,
        end_time: datetime | None = ...,
        privacy_level: PrivacyLevel = ...,
        status: EventStatus = ...,
        image: bytes = ...,
        reason: str | None = ...,
    ) -> ScheduledEvent: ...

    @overload
    async def edit(
        self,
        *,
        name: str = ...,
        description: str = ...,
        start_time: datetime = ...,
        end_time: datetime = ...,
        privacy_level: PrivacyLevel = ...,
        status: EventStatus = ...,
        image: bytes = ...,
        location: str,
        reason: str | None = ...,
    ) -> ScheduledEvent: ...

    async def edit(
        self,
        *,
        name: str = MISSING,
        description: str = MISSING,
        channel: Snowflake | None = MISSING,
        start_time: datetime = MISSING,
        end_time: datetime | None = MISSING,
        privacy_level: PrivacyLevel = MISSING,
        entity_type: EntityType = MISSING,
        status: EventStatus = MISSING,
        image: bytes = MISSING,
        location: str = MISSING,
        reason: str | None = None,
    ) -> ScheduledEvent:
        r"""|coro|.

        Edits the scheduled event.

        You must have :attr:`~Permissions.manage_events` to do this.

        Parameters
        ----------
        name: :class:`str`
            The name of the scheduled event.
        description: :class:`str`
            The description of the scheduled event.
        channel: Optional[:class:`~discord.abc.Snowflake`]
            The channel to put the scheduled event in. If the channel is
            a :class:`StageInstance` or :class:`VoiceChannel` then
            it automatically sets the entity type.

            Required if the entity type is either :attr:`EntityType.voice` or
            :attr:`EntityType.stage_instance`.
        start_time: :class:`datetime.datetime`
            The time that the scheduled event will start. This must be a timezone-aware
            datetime object. Consider using :func:`utils.utcnow`.
        end_time: Optional[:class:`datetime.datetime`]
            The time that the scheduled event will end. This must be a timezone-aware
            datetime object. Consider using :func:`utils.utcnow`.

            If the entity type is either :attr:`EntityType.voice` or
            :attr:`EntityType.stage_instance`, the end_time can be cleared by
            passing ``None``.

            Required if the entity type is :attr:`EntityType.external`.
        privacy_level: :class:`PrivacyLevel`
            The privacy level of the scheduled event.
        entity_type: :class:`EntityType`
            The new entity type. If the channel is a :class:`StageInstance`
            or :class:`VoiceChannel` then this is automatically set to the
            appropriate entity type.
        status: :class:`EventStatus`
            The new status of the scheduled event.
        image: Optional[:class:`bytes`]
            The new image of the scheduled event or ``None`` to remove the image.
        location: :class:`str`
            The new location of the scheduled event.

            Required if the entity type is :attr:`EntityType.external`.
        reason: Optional[:class:`str`]
            The reason for editing the scheduled event. Shows up on the audit log.

        Raises
        ------
        TypeError
            ``image`` was not a :term:`py:bytes-like object`, or ``privacy_level``
            was not a :class:`PrivacyLevel`, or ``entity_type`` was not an
            :class:`EntityType`, ``status`` was not an :class:`EventStatus`, or
            an argument was provided that was incompatible with the scheduled event's
            entity type.
        ValueError
            ``start_time`` or ``end_time`` was not a timezone-aware datetime object.
        Forbidden
            You do not have permissions to edit the scheduled event.
        HTTPException
            Editing the scheduled event failed.

        Returns
        -------
        :class:`ScheduledEvent`
            The edited scheduled event.

        """
        payload = {}
        metadata = {}

        if name is not MISSING:
            payload["name"] = name

        if start_time is not MISSING:
            if start_time.tzinfo is None:
                msg = "start_time must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time."
                raise ValueError(msg)
            payload["scheduled_start_time"] = start_time.isoformat()

        if description is not MISSING:
            payload["description"] = description

        if privacy_level is not MISSING:
            if not isinstance(privacy_level, PrivacyLevel):
                msg = "privacy_level must be of type PrivacyLevel."
                raise TypeError(msg)

            payload["privacy_level"] = privacy_level.value

        if status is not MISSING:
            if not isinstance(status, EventStatus):
                msg = "status must be of type EventStatus"
                raise TypeError(msg)

            payload["status"] = status.value

        if image is not MISSING:
            image_as_str: str | None = _bytes_to_base64_data(image) if image is not None else image
            payload["image"] = image_as_str

        entity_type = entity_type or getattr(channel, "_scheduled_event_entity_type", MISSING)
        if entity_type is MISSING:
            if channel and isinstance(channel, Object):
                if channel.type is VoiceChannel:
                    entity_type = EntityType.voice
                elif channel.type is StageChannel:
                    entity_type = EntityType.stage_instance
            elif location not in (MISSING, None):
                entity_type = EntityType.external
        else:
            if not isinstance(entity_type, EntityType):
                msg = "entity_type must be of type EntityType"
                raise TypeError(msg)

            payload["entity_type"] = entity_type.value

        if entity_type is None:
            msg = f"invalid GuildChannel type passed, must be VoiceChannel or StageChannel not {channel.__class__.__name__}"
            raise TypeError(msg)

        _entity_type = entity_type or self.entity_type
        _entity_type_changed = _entity_type is not self.entity_type

        if _entity_type in (EntityType.stage_instance, EntityType.voice):
            if channel is MISSING or channel is None:
                if _entity_type_changed:
                    msg = "channel must be set when entity_type is voice or stage_instance"
                    raise TypeError(msg)
            else:
                payload["channel_id"] = channel.id

            if location not in (MISSING, None):
                msg = "location cannot be set when entity_type is voice or stage_instance"
                raise TypeError(msg)
            payload["entity_metadata"] = None
        else:
            if channel not in (MISSING, None):
                msg = "channel cannot be set when entity_type is external"
                raise TypeError(msg)
            payload["channel_id"] = None

            if location is MISSING or location is None:
                if _entity_type_changed:
                    msg = "location must be set when entity_type is external"
                    raise TypeError(msg)
            else:
                metadata["location"] = location

            if not self.end_time and (end_time is MISSING or end_time is None):
                msg = "end_time must be set when entity_type is external"
                raise TypeError(msg)

        if end_time is not MISSING:
            if end_time is not None:
                if end_time.tzinfo is None:
                    msg = "end_time must be an aware datetime. Consider using discord.utils.utcnow() or datetime.datetime.now().astimezone() for local time."
                    raise ValueError(msg)
                payload["scheduled_end_time"] = end_time.isoformat()
            else:
                payload["scheduled_end_time"] = end_time

        if metadata:
            payload["entity_metadata"] = metadata

        data = await self._state.http.edit_scheduled_event(self.guild_id, self.id, **payload, reason=reason)
        s = ScheduledEvent(state=self._state, data=data)
        s._users = self._users
        return s

    async def delete(self, *, reason: str | None = None) -> None:
        """|coro|.

        Deletes the scheduled event.

        You must have :attr:`~Permissions.manage_events` to do this.

        Parameters
        ----------
        reason: Optional[:class:`str`]
            The reason for deleting the scheduled event. Shows up on the audit log.

        Raises
        ------
        Forbidden
            You do not have permissions to delete the scheduled event.
        HTTPException
            Deleting the scheduled event failed.

        """
        await self._state.http.delete_scheduled_event(self.guild_id, self.id, reason=reason)

    async def users(
        self,
        *,
        limit: int | None = None,
        before: Snowflake | None = None,
        after: Snowflake | None = None,
        oldest_first: bool = MISSING,
    ) -> AsyncIterator[User]:
        """|coro|.

        Retrieves all :class:`User` that are subscribed to this event.

        This requires :attr:`Intents.members` to get information about members
        other than yourself.

        Raises
        ------
        HTTPException
            Retrieving the members failed.

        Returns
        -------
        List[:class:`User`]
            All subscribed users of this event.

        """

        async def _before_strategy(retrieve: int, before: Snowflake | None, limit: int | None):
            before_id = before.id if before else None
            users = await self._state.http.get_scheduled_event_users(
                self.guild_id, self.id, limit=retrieve, with_member=False, before=before_id
            )

            if users:
                if limit is not None:
                    limit -= len(users)

                before = Object(id=users[-1]["user"]["id"])

            return users, before, limit

        async def _after_strategy(retrieve: int, after: Snowflake | None, limit: int | None):
            after_id = after.id if after else None
            users = await self._state.http.get_scheduled_event_users(
                self.guild_id, self.id, limit=retrieve, with_member=False, after=after_id
            )

            if users:
                if limit is not None:
                    limit -= len(users)

                after = Object(id=users[0]["user"]["id"])

            return users, after, limit

        if limit is None:
            limit = self.user_count or None

        reverse = after is not None if oldest_first is MISSING else oldest_first

        predicate = None

        if reverse:
            strategy, state = _after_strategy, after
            if before:

                def predicate(u):
                    return u["user"]["id"] < before.id
        else:
            strategy, state = _before_strategy, before
            if after and after != OLDEST_OBJECT:

                def predicate(u):
                    return u["user"]["id"] > after.id

        while True:
            retrieve = 100 if limit is None else min(limit, 100)
            if retrieve < 1:
                return

            data, state, limit = await strategy(retrieve, state, limit)

            if reverse:
                data = reversed(data)
            if predicate:
                data = filter(predicate, data)

            users = (self._state.store_user(raw_user["user"]) for raw_user in data)
            count = 0

            for count, user in enumerate(users, 1):
                yield user

            if count < 100:
                # There's no data left after this
                break

    def _add_user(self, user: User) -> None:
        self._users[user.id] = user

    def _pop_user(self, user_id: int) -> None:
        self._users.pop(user_id, None)
