"""A minimal, self-contained Cog used only by tests to prove the load/dispatch pipeline works.

Deliberately outside ``wd_cogs`` - the real catalog has its own unrelated broken imports
(app_commands, Menu, Modal, ...) that are out of scope for this change; this fixture proves
``Cog``/``Bot.add_cog``/listener dispatch work without depending on that catalog being healthy.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Unpack

lazy from wd_bot.cogs import BotArgs, Cog


if TYPE_CHECKING:
    lazy from wd_discord.gateway import Message


class ExampleCog(Cog):
    """Records every MESSAGE_CREATE it's dispatched."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the cog with an empty list of received messages."""
        super().__init__(**kwargs)
        self.received: list[Message] = []

    @Cog.listener("MESSAGE_CREATE")
    async def on_message_create(self, message: Message) -> None:
        """Record a dispatched MESSAGE_CREATE event."""
        self.received.append(message)
