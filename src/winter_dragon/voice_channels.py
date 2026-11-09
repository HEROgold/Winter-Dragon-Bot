"""Voice channels a cog creates and records, deleted once everyone left.

Who is in which voice channel comes from GUILD_CREATE and VOICE_STATE_UPDATE.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
lazy from collections import defaultdict

lazy from sqlmodel import Session
lazy from wd_db.extension.lifecycle import alive_by_id, owned_by, soft_delete
lazy from wd_discord import is_gone
lazy from wd_discord.snowflake import Snowflake


if TYPE_CHECKING:
    lazy from collections.abc import Callable, Iterable

    lazy from herogold.log import Logger
    lazy from sqlalchemy import Connection, Engine
    lazy from wd_db.extension.lifecycle import DiscordKeyedModel
    lazy from wd_discord import Client, VoiceState


@dataclass
class VoiceOccupancy:
    """Who is in which voice channel, per guild, as far as the gateway told."""

    _channels: defaultdict[Snowflake, dict[Snowflake, Snowflake]] = field(default_factory=lambda: defaultdict(dict))
    """Per guild, the voice channel each connected member is in."""

    def reset(self, guild_id: Snowflake, states: Iterable[VoiceState]) -> None:
        """Forget what was known about ``guild_id``, and learn ``states`` instead."""
        self._channels[guild_id] = {state.user.id: state.channel.id for state in states if state.channel is not None}

    def move(self, guild_id: Snowflake, user_id: Snowflake, channel_id: Snowflake | None) -> Snowflake | None:
        """Record that ``user_id`` is now in ``channel_id``, or left voice when ``None``; return where they were."""
        before = self._channels[guild_id].pop(user_id, None)
        if channel_id is not None:
            self._channels[guild_id][user_id] = channel_id
        return before

    def occupied(self, guild_id: Snowflake, channel_id: Snowflake) -> bool:
        """Whether anyone is in the voice channel ``channel_id``."""
        return channel_id in self._channels[guild_id].values()

    def channel_of(self, guild_id: Snowflake, user_id: Snowflake) -> Snowflake | None:
        """Return the voice channel ``user_id`` is in, if the gateway told."""
        return self._channels[guild_id].get(user_id)

    def members_in(self, guild_id: Snowflake, channel_id: Snowflake) -> list[Snowflake]:
        """Return who is in the voice channel ``channel_id``."""
        return [user_id for user_id, channel in self._channels[guild_id].items() if channel == channel_id]


@dataclass
class EmptiedChannels[M: DiscordKeyedModel]:
    """Voice channels a cog created and records as ``model`` rows (``id`` is the channel's), deleted once empty.

    ``model`` must declare a guild owner in its ``Ownership``.
    """

    model: type[M]
    bind: Engine | Connection
    client: Client
    logger: Logger
    reason: str
    """The audit log reason for deleting an empty channel."""
    on_forgotten: Callable[[Session, M], None] | None = None
    """Called with the session and the row when a deleted channel's row is soft-deleted, before commit."""

    def record(self, session: Session, channel_id: Snowflake) -> M | None:
        """Return the live row recording the voice channel ``channel_id``, or ``None`` if it has none."""
        return alive_by_id(session, self.model, int(channel_id))

    async def delete(self, record: M) -> None:
        """Delete the voice channel of ``record`` and forget it once it's gone; one that's left is tried again later."""
        deleted = await self.client.channels.partial(record.id).delete(reason=self.reason)
        if not is_gone(deleted):
            self.logger.warning(t"Could not delete voice channel {record.id}: {deleted}")
            return
        self.forget(record)

    def forget(self, record: M) -> None:
        """Forget the voice channel of ``record``, which is gone: soft-delete its row."""
        with Session(self.bind) as session:
            found = alive_by_id(session, self.model, record.id)
            if found is not None:
                soft_delete(session, found)
                if self.on_forgotten is not None:
                    self.on_forgotten(session, found)
                session.commit()

    async def sweep(self, voice: VoiceOccupancy, guild_id: Snowflake) -> None:
        """Delete the recorded voice channels of ``guild_id`` that nobody is in."""
        with Session(self.bind) as session:
            rows = list(session.exec(owned_by(self.model, guild=guild_id)))
        for row in rows:
            if not voice.occupied(guild_id, Snowflake(row.id)):
                await self.delete(row)

    async def left(
        self,
        voice: VoiceOccupancy,
        guild_id: Snowflake,
        before: Snowflake | None,
        after: Snowflake | None,
    ) -> None:
        """Delete the recorded voice channel ``before`` once the member who left it left it empty."""
        if before is None or before == after:
            return
        with Session(self.bind) as session:
            found = self.record(session, before)
        if found is not None and not voice.occupied(guild_id, before):
            await self.delete(found)
