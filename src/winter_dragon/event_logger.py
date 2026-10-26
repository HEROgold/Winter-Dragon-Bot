"""A bot that does nothing but log every frame the Discord gateway sends it.

Run from the repo root: uv run python -m winter_dragon.event_logger

Connects with every intent (privileged ones included) and logs each received frame as raw JSON:
dispatches (``op`` 0, every event name, typed model or not) as well as heartbeat requests, reconnects
and invalid-session frames. Uses the token in bot.ini. The privileged intents (GUILD_MEMBERS,
GUILD_PRESENCES, MESSAGE_CONTENT) must be enabled for the application in the Discord developer portal,
or Discord closes the connection with 4014.

Logs go to stdout and ./logs through herogold's logger.
"""

lazy import asyncio
lazy import json
lazy import sys
lazy from typing import TYPE_CHECKING, override

lazy from herogold.log import LoggerMixin
lazy from wd_bot.settings import Tokens
lazy from wd_discord import models
lazy from wd_discord.gateway.connection import Disconnect, Gateway, GatewayFrame
lazy from wd_discord.gateway.events import EventName
lazy from wd_discord.intents import Intents


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from wd_discord.models import DiscordModel


class EventLoggingGateway(Gateway):
    """A gateway that logs every frame it receives as raw JSON before handling it."""

    @override
    async def _handle(
        self,
        message: GatewayFrame,
        dispatch: Callable[[str, DiscordModel], Awaitable[None]],
    ) -> Disconnect | None:
        """Log ``message`` as Discord sent it, then handle it as usual."""
        event = message.get("t") or f"op {message['op']}"
        self.logger.info(t"{event}: {json.dumps(message, default=str)}")
        return await super()._handle(message, dispatch)

    async def log_ready(self, name: str, event: DiscordModel) -> None:
        """Log READY, which :meth:`connect` consumes before :meth:`_handle` sees it; other events are logged raw."""
        if name == EventName.READY:
            self.logger.info(t"{name}: {event.model_dump_json()}")

    def capture_model_warnings(self) -> None:
        """Send ``wd_discord.models``' log records (unknown-field warnings) through this gateway's handlers.

        herogold's ``getLogger`` returns loggers outside ``logging``'s hierarchy, so the module's logger has no
        handlers and its records only reach stderr; share ours so they land in this gateway's log file too.
        """
        # TODO(Herogold, HeroPy#55): drop once herogold's getLogger returns propagating loggers.  # noqa: FIX002
        for handler in self.logger.handlers:
            if handler not in models.logger.handlers:
                models.logger.addHandler(handler)


async def main() -> None:
    """Connect with every intent and log events until interrupted."""
    LoggerMixin.set_log_directory("logs")
    gateway = EventLoggingGateway(Tokens.read_only_token, intents=Intents.all())
    gateway.capture_model_warnings()
    await gateway.connect()
    try:
        await gateway.run(gateway.log_ready)
    finally:
        await gateway.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
