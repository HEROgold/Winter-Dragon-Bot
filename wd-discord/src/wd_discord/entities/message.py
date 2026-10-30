"""Messages (https://docs.discord.com/developers/resources/message)."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

lazy from wd_config.discord import URLS

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.entities.base import ClientBound, Entity, Partial, no_content
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.emoji import Emoji
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.user import User
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.partial_emoji import PartialEmoji
lazy from wd_discord.responses import message_data


if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from datetime import datetime
    from string.templatelib import Template

    from wd_discord.audit import Reason
    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.entities.member import BaseMember
    from wd_discord.entities.user import BaseUser
    from wd_discord.resources.message import Attachment, Reaction
    from wd_discord.snowflake import Snowflake


type ReactionEmoji = str | Emoji | PartialEmoji
"""An emoji to react with: a unicode character, ``name:id`` for a custom emoji, or an emoji object."""


def reaction_name(emoji: ReactionEmoji) -> str:
    """Return ``emoji`` as Discord's reaction routes name it: the unicode character, or ``name:id``."""
    match emoji:
        case str():
            return emoji
        case Emoji() | PartialEmoji() if emoji.id is not None:
            return f"{emoji.name}:{emoji.id}"
        case _:
            return emoji.name or ""


class BaseMessage(ClientBound):
    """What can be done to a message knowing only its channel and ID: read, edit, delete, react to and pin it."""

    if TYPE_CHECKING:

        @property
        def id(self) -> Snowflake:
            """The message's ID."""

        @property
        def channel_id(self) -> Snowflake:
            """The channel the message was sent in."""

    @property
    def channel(self) -> PartialChannel:
        """The channel the message was sent in."""
        return PartialChannel(self.client, self.channel_id)

    @property
    def jump_url(self) -> str:
        """A link that opens the message; works in DMs and guilds alike."""
        return f"{URLS.web}/channels/@me/{self.channel_id}/{self.id}"

    @property
    def _path(self) -> Template:
        return t"/channels/{self.channel_id}/messages/{self.id}"

    async def fetch(self, *, reuse_response: bool = False) -> Message | NetworkError:
        """GET /channels/{channel_id}/messages/{message_id}; needs READ_MESSAGE_HISTORY in a guild.

        Doesn't write to the client's gateway :class:`~wd_discord.cache.StateCache`.
        """
        return self._entity(await self.client.get(self._path, reuse_response=reuse_response), MessageModel, Message)

    async def edit(
        self,
        content: str | None = None,
        *,
        embeds: Sequence[Embed] | None = None,
        components: Sequence[ActionRow] | None = None,
    ) -> Message | NetworkError:
        """PATCH /channels/{channel_id}/messages/{message_id} - edit a message the bot sent.

        A ``None`` argument leaves that part of the message unchanged; an empty sequence clears it.
        """
        payload = message_data(content=content, embeds=embeds, components=components)
        return self._entity(await self.client.patch(self._path, json=payload), MessageModel, Message)

    async def delete(self, *, reason: Reason = None) -> NetworkError | None:
        """DELETE /channels/{channel_id}/messages/{message_id}; someone else's message needs MANAGE_MESSAGES."""
        return no_content(await self.client.delete(self._path, json={}, headers=reason_headers(reason)))

    async def add_reaction(self, emoji: ReactionEmoji) -> NetworkError | None:
        """PUT /channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me - react as the bot."""
        return no_content(await self.client.put(self._path + t"/reactions/{reaction_name(emoji)}/@me", json={}))

    async def remove_reaction(self, emoji: ReactionEmoji, user: BaseUser | BaseMember | None = None) -> NetworkError | None:
        """DELETE .../reactions/{emoji}/{user_id} - take back the bot's reaction, or ``user``'s (needs MANAGE_MESSAGES)."""
        reaction = self._path + t"/reactions/{reaction_name(emoji)}"
        route = reaction + t"/@me" if user is None else reaction + t"/{user.id}"
        return no_content(await self.client.delete(route, json={}))

    async def clear_reactions(self, emoji: ReactionEmoji | None = None) -> NetworkError | None:
        """DELETE .../reactions[/{emoji}] - remove every reaction, or every one with ``emoji``; needs MANAGE_MESSAGES."""
        route = self._path + t"/reactions" if emoji is None else self._path + t"/reactions/{reaction_name(emoji)}"
        return no_content(await self.client.delete(route, json={}))

    async def pin(self, *, reason: Reason = None) -> NetworkError | None:
        """PUT /channels/{channel_id}/messages/pins/{message_id}; needs PIN_MESSAGES."""
        route = t"/channels/{self.channel_id}/messages/pins/{self.id}"
        return no_content(await self.client.put(route, json={}, headers=reason_headers(reason)))

    async def unpin(self, *, reason: Reason = None) -> NetworkError | None:
        """DELETE /channels/{channel_id}/messages/pins/{message_id}; needs PIN_MESSAGES."""
        route = t"/channels/{self.channel_id}/messages/pins/{self.id}"
        return no_content(await self.client.delete(route, json={}, headers=reason_headers(reason)))


class Message(Entity[MessageModel], BaseMessage):
    """A message, as Discord returned or dispatched it."""

    @property
    @override
    def id(self) -> Snowflake:
        """The message's ID."""
        return self.model.id

    @property
    @override
    def channel_id(self) -> Snowflake:
        """The channel the message was sent in."""
        return self.model.channel_id

    @property
    def content(self) -> str:
        """The message's text; empty without the MESSAGE_CONTENT intent, unless the bot is mentioned."""
        return self.model.content

    @property
    def author(self) -> User:
        """Who sent the message."""
        return User(self.client, self.model.author)

    @property
    def mentions(self) -> Generator[User]:
        """The users the message mentions."""
        return (User(self.client, user) for user in self.model.mentions)

    @property
    def attachments(self) -> Generator[Attachment]:
        """The files attached to the message."""
        yield from self.model.attachments

    @property
    def embeds(self) -> Generator[Embed]:
        """The message's embeds."""
        yield from self.model.embeds

    @property
    def reactions(self) -> Generator[Reaction]:
        """The message's reactions; empty on a dispatched MESSAGE_CREATE."""
        yield from self.model.reactions

    @property
    def guild(self) -> PartialGuild | None:
        """The guild the message was sent in; ``None`` in a DM or when Discord left it out."""
        return self._partial(PartialGuild, self.model.guild_id)

    @property
    def timestamp(self) -> datetime:
        """When the message was sent."""
        return self.model.timestamp

    @property
    def edited_timestamp(self) -> datetime | None:
        """When the message was last edited; ``None`` if never."""
        return self.model.edited_timestamp

    @property
    def tts(self) -> bool:
        """Whether the message was sent as text-to-speech."""
        return self.model.tts

    @property
    def mention_everyone(self) -> bool:
        """Whether the message mentions ``@everyone``."""
        return self.model.mention_everyone

    @property
    @override
    def jump_url(self) -> str:
        """A link that opens the message."""
        guild = "@me" if self.model.guild_id is None else str(self.model.guild_id)
        return f"{URLS.web}/channels/{guild}/{self.channel_id}/{self.id}"


@dataclass(frozen=True)
class PartialMessage(BaseMessage, Partial[Message]):
    """A message known only by channel and ID."""

    channel_id: Snowflake
    """The channel the message was sent in."""
