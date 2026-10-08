"""Messages (https://docs.discord.com/developers/resources/message)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity, no_content, parse
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.user import User
lazy from wd_discord.gateway.events import Message as MessageModel
lazy from wd_discord.responses import message_data


if TYPE_CHECKING:
    from collections.abc import Sequence

    from wd_discord.client import NetworkError
    from wd_discord.components import ActionRow
    from wd_discord.embed import Embed
    from wd_discord.snowflake import Snowflake


class Message(Entity[MessageModel]):
    """A message, as Discord returned or dispatched it."""

    @property
    def id(self) -> Snowflake:
        """The message's ID."""
        return self.model.id

    @property
    def content(self) -> str:
        """The message's text."""
        return self.model.content

    @property
    def author(self) -> User:
        """Who sent the message."""
        return User(self.client, self.model.author)

    @property
    def channel(self) -> PartialChannel:
        """The channel the message was sent in."""
        return PartialChannel(self.client, self.model.channel_id)

    @property
    def _path(self) -> str:
        return f"/channels/{self.model.channel_id}/messages/{self.id}"

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
        message = parse(await self.client.patch(self._path, json=payload), MessageModel)
        return message if is_network_error(message) else Message(self.client, message)

    async def delete(self) -> NetworkError | None:
        """DELETE /channels/{channel_id}/messages/{message_id}."""
        return no_content(await self.client.delete(self._path, json={}))
