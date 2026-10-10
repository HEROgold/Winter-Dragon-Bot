"""Guild emojis and stickers (https://docs.discord.com/developers/resources/emoji, .../resources/sticker)."""

from __future__ import annotations

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.client import is_network_error
lazy from wd_discord.entities.base import Entity, no_content, parse
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.role import PartialRole
lazy from wd_discord.entities.user import User
lazy from wd_discord.resources.guild import Emoji as EmojiModel
lazy from wd_discord.resources.guild import Sticker as StickerModel


if TYPE_CHECKING:
    from collections.abc import Generator

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError
    from wd_discord.resources.guild.sticker import StickerFormatType, StickerType
    from wd_discord.snowflake import Snowflake


@dataclass(frozen=True)
class Emoji(Entity[EmojiModel]):
    """A guild's custom emoji, as Discord returned it."""

    guild_id: Snowflake
    """The guild the emoji belongs to."""

    @property
    def id(self) -> Snowflake | None:
        """The emoji's ID; ``None`` only for a unicode emoji in a reaction."""
        return self.model.id

    @property
    def name(self) -> str | None:
        """The emoji's name."""
        return self.model.name

    @property
    def guild(self) -> PartialGuild:
        """The guild the emoji belongs to."""
        return PartialGuild(self.client, self.guild_id)

    @property
    def roles(self) -> Generator[PartialRole]:
        """The roles allowed to use the emoji; empty when everyone may."""
        for role_id in self.model.roles or []:
            yield PartialRole(self.client, role_id, self.guild_id)

    @property
    def user(self) -> User | None:
        """Who uploaded the emoji; only sent with MANAGE_GUILD_EXPRESSIONS."""
        return None if self.model.user is None else User(self.client, self.model.user)

    @property
    def animated(self) -> bool:
        """Whether the emoji is animated."""
        return bool(self.model.animated)

    @property
    def available(self) -> bool:
        """Whether the emoji can be used; ``False`` after the guild lost the boosts it needs."""
        return self.model.available is not False

    @property
    def mention(self) -> str:
        """The emoji as it's written in a message: ``<:name:id>``, or ``<a:name:id>`` when animated."""
        return f"<{'a' if self.animated else ''}:{self.name}:{self.id}>"

    async def fetch(self) -> Emoji | NetworkError:
        """GET /guilds/{guild_id}/emojis/{emoji_id}."""
        result = await self.client.get(t"/guilds/{self.guild_id}/emojis/{self.id}")
        parsed = parse(result, EmojiModel)
        return parsed if is_network_error(parsed) else Emoji(self.client, parsed, self.guild_id)

    async def delete(self, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /guilds/{guild_id}/emojis/{emoji_id}; needs MANAGE_GUILD_EXPRESSIONS."""
        return no_content(await self.client.delete(t"/guilds/{self.guild_id}/emojis/{self.id}", headers=reason_headers(reason)))


class Sticker(Entity[StickerModel]):
    """A sticker, as Discord returned it: a guild's own, or a standard one from a pack."""

    @property
    def id(self) -> Snowflake:
        """The sticker's ID."""
        return self.model.id

    @property
    def name(self) -> str:
        """The sticker's name."""
        return self.model.name

    @property
    def description(self) -> str | None:
        """The sticker's description."""
        return self.model.description

    @property
    def tags(self) -> str:
        """The autocomplete tags for the sticker."""
        return self.model.tags

    @property
    def type(self) -> StickerType:
        """Whether the sticker is a standard or a guild sticker."""
        return self.model.type

    @property
    def format_type(self) -> StickerFormatType:
        """The sticker's image format."""
        return self.model.format_type

    @property
    def available(self) -> bool:
        """Whether a guild sticker can be used; ``False`` after the guild lost the boosts it needs."""
        return self.model.available is not False

    @property
    def guild(self) -> PartialGuild | None:
        """The guild that owns the sticker; ``None`` for a standard sticker."""
        guild_id = self.model.guild_id
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def user(self) -> User | None:
        """Who uploaded a guild sticker; only sent with MANAGE_GUILD_EXPRESSIONS."""
        return None if self.model.user is None else User(self.client, self.model.user)

    async def fetch(self) -> Sticker | NetworkError:
        """GET /stickers/{sticker_id}."""
        return self._entity(await self.client.get(t"/stickers/{self.id}"), StickerModel, Sticker)

    async def delete(self, *, reason: AuditLogReason | str | None = None) -> NetworkError | None:
        """DELETE /guilds/{guild_id}/stickers/{sticker_id} - delete a guild sticker; needs MANAGE_GUILD_EXPRESSIONS.

        A standard sticker belongs to no guild, so deleting one fails with Discord's error.
        """
        route = t"/guilds/{self.model.guild_id}/stickers/{self.id}"
        return no_content(await self.client.delete(route, headers=reason_headers(reason)))
