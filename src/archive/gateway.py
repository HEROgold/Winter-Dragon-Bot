"""The archive's gateway: the event logger's, plus a database write for every event it receives."""

from functools import partial
from typing import TYPE_CHECKING, override

from wd_discord.gateway.connection import Opcode
from wd_discord.gateway.events import EventName

from archive.handlers import handle, payload_of, store_raw
from winter_dragon.event_logger import EventLoggingGateway


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from wd_core.intents import Intents
    from wd_discord.gateway.connection import Disconnect, GatewayFrame
    from wd_discord.models import DiscordModel

    from archive.writer import Writer


class ArchiveGateway(EventLoggingGateway):
    """Logs every frame, like the event logger, and queues each dispatch for the archive's writer.

    The raw frame is queued before wd-discord parses it, so it is stored even when parsing fails; the parsed
    event is then queued for the typed tables. READY never reaches :meth:`_handle` (``connect`` consumes it), so it
    is stored raw from its parsed form.
    """

    def __init__(self, token: str, *, intents: Intents, writer: Writer) -> None:
        """Connect with ``token`` and ``intents``, queueing writes on ``writer``."""
        super().__init__(token, intents=intents)
        self.writer = writer

    @override
    async def _handle(
        self,
        message: GatewayFrame,
        dispatch: Callable[[str, DiscordModel], Awaitable[None]],
    ) -> Disconnect | None:
        """Queue a dispatch's raw frame, then log and handle it as usual."""
        if message["op"] == Opcode.DISPATCH:
            self.writer.put(partial(store_raw, name=message["t"], sequence=message["s"], data=message["d"]))
        return await super()._handle(message, dispatch)

    async def archive(self, name: str, event: DiscordModel) -> None:
        """Queue ``event`` for the typed tables; READY is also stored raw, and logged."""
        if name == EventName.READY:
            await self.log_ready(name, event)
            self.writer.put(partial(store_raw, name=name, sequence=None, data=payload_of(event)))
        self.writer.put(lambda session: handle(session, name, payload_of(event)))
