"""Invites (https://docs.discord.com/developers/resources/invite)."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.user import User
lazy from wd_discord.resources.invite import Invite as InviteModel
lazy from wd_discord.resources.user import User as UserModel
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    from collections.abc import Mapping

    from wd_discord.audit import AuditLogReason
    from wd_discord.client import NetworkError


def _id(partial: Mapping[str, object] | None) -> Snowflake | None:
    """Return the ``id`` of a partial object sent inside an invite, if there is one."""
    value = None if partial is None else partial.get("id")
    return None if value is None else Snowflake.coerce(str(value))


class Invite(Entity[InviteModel]):
    """An invite to a guild channel, as Discord returned it."""

    @property
    def code(self) -> str:
        """The invite's code, the last part of its URL."""
        return self.model.code

    @property
    def url(self) -> str:
        """The invite's shareable URL."""
        return self.model.url

    @property
    def guild(self) -> PartialGuild | None:
        """The guild the invite is for; Discord sends only a summary of it."""
        guild_id = _id(self.model.guild)
        return None if guild_id is None else PartialGuild(self.client, guild_id)

    @property
    def channel(self) -> PartialChannel | None:
        """The channel the invite opens; Discord sends only a summary of it."""
        channel_id = _id(self.model.channel)
        return None if channel_id is None else PartialChannel(self.client, channel_id)

    @property
    def inviter(self) -> User | None:
        """Who created the invite."""
        return None if self.model.inviter is None else User(self.client, UserModel.model_validate(self.model.inviter))

    @property
    def uses(self) -> int | None:
        """How often the invite was used; only sent to whoever may manage it."""
        return self.model.uses

    @property
    def max_uses(self) -> int | None:
        """How often the invite may be used; ``0`` for unlimited."""
        return self.model.max_uses

    @property
    def max_age(self) -> int | None:
        """The seconds the invite stays valid after creation; ``0`` for forever."""
        return self.model.max_age

    @property
    def temporary(self) -> bool:
        """Whether members who join through the invite are removed again when they disconnect without a role."""
        return bool(self.model.temporary)

    async def fetch(self) -> Invite | NetworkError:
        """GET /invites/{invite_code}."""
        return self._entity(await self.client.get(t"/invites/{self.code}"), InviteModel, Invite)

    async def delete(self, *, reason: AuditLogReason | str | None = None) -> Invite | NetworkError:
        """DELETE /invites/{invite_code} - revoke the invite; needs MANAGE_CHANNELS on its channel, or MANAGE_GUILD."""
        result = await self.client.delete(t"/invites/{self.code}", headers=reason_headers(reason))
        return self._entity(result, InviteModel, Invite)
