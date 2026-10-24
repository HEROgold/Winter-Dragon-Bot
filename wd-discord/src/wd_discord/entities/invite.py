"""Invites (https://docs.discord.com/developers/resources/invite)."""

lazy from typing import TYPE_CHECKING

lazy from wd_discord.audit import reason_headers
lazy from wd_discord.entities.base import Entity
lazy from wd_discord.entities.channel import PartialChannel
lazy from wd_discord.entities.guild import PartialGuild
lazy from wd_discord.entities.user import User
lazy from wd_discord.resources.invite import Invite as InviteModel


if TYPE_CHECKING:

    from wd_discord.audit import Reason
    from wd_discord.client import NetworkError


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
        guild = self.model.guild
        return None if guild is None else PartialGuild(self.client, guild.id)

    @property
    def channel(self) -> PartialChannel | None:
        """The channel the invite opens; Discord sends only a summary of it."""
        channel = self.model.channel
        return None if channel is None else PartialChannel(self.client, channel.id)

    @property
    def inviter(self) -> User | None:
        """Who created the invite."""
        return None if self.model.inviter is None else User(self.client, self.model.inviter)

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

    async def fetch(self, *, cache: bool = False) -> Invite | NetworkError:
        """GET /invites/{invite_code}."""
        return self._entity(await self.client.get(t"/invites/{self.code}", cache=cache), InviteModel, Invite)

    async def delete(self, *, reason: Reason = None) -> Invite | NetworkError:
        """DELETE /invites/{invite_code} - revoke the invite; needs MANAGE_CHANNELS on its channel, or MANAGE_GUILD."""
        result = await self.client.delete(t"/invites/{self.code}", headers=reason_headers(reason))
        return self._entity(result, InviteModel, Invite)
