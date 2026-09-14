"""The Discord invite resource."""
from __future__ import annotations

from collections.abc import Mapping

from wd_discord.models import DiscordModel


class Invite(DiscordModel):
    """A guild invite (subset - https://docs.discord.com/developers/resources/invite).

    TODO(Phase 2): ``guild``/``channel``/``inviter`` arrive as partial nested objects on the
    wire (not the full REST resource shape), so they're kept as raw dicts here rather than the
    real Guild/Channel/User models - same reasoning as GuildCreate's own nested collections.
    """

    code: str
    guild: Mapping[str, object] | None = None
    channel: Mapping[str, object] | None = None
    inviter: Mapping[str, object] | None = None
    uses: int | None = None
    max_uses: int | None = None
    max_age: int | None = None
    temporary: bool | None = None
    created_at: str | None = None

    @property
    def url(self) -> str:
        """The invite's shareable URL."""
        return f"https://discord.gg/{self.code}"
