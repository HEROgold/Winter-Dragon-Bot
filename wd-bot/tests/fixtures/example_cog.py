"""A minimal, self-contained Cog used only by tests to prove the load/dispatch pipeline works.

Deliberately outside ``wd_cogs`` - the real catalog has its own unrelated broken imports
(app_commands, Menu, Modal, ...) that are out of scope for this change; this fixture proves
``Cog``/``Bot.add_cog``/listener dispatch work without depending on that catalog being healthy.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Unpack

lazy from wd_bot.cogs import BotArgs, Cog
lazy from wd_discord.gateway import EventName
lazy from wd_discord.resources.user import User  # noqa: TC002


if TYPE_CHECKING:
    lazy from wd_discord import DiscordModel
    lazy from wd_discord.gateway import GuildCreate, Message
    lazy from wd_discord.gateway.events import Interaction


class ExampleCog(Cog):
    """Records every MESSAGE_CREATE/GUILD_CREATE it's dispatched."""

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the cog with an empty list of received events."""
        super().__init__(**kwargs)
        self.received: list[DiscordModel] = []

    @Cog.listener(EventName.MESSAGE_CREATE)  # type: ignore[reportUntypedFunctionDecorator]
    async def on_message_create(self, message: Message) -> None:
        """Record a dispatched MESSAGE_CREATE event."""
        self.received.append(message)

    @Cog.listener(EventName.GUILD_CREATE)  # type: ignore[reportUntypedFunctionDecorator]
    async def on_guild_create(self, guild: GuildCreate) -> None:
        """Record a dispatched GUILD_CREATE event."""
        self.received.append(guild)

    @Cog.command(name="ping-user", description="Ping a user (test fixture)")  # type: ignore[reportUntypedFunctionDecorator]
    async def ping_user(self, interaction: Interaction, user: User) -> None:
        """Ping a user."""
