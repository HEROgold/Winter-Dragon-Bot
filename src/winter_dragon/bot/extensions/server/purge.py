"""A cog that provides a command to purge messages."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import discord
from discord import Interaction, Message, app_commands
from herogold.sentinel import MISSING

from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.core.config import Config


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from discord.abc import SnowflakeTime


@runtime_checkable
class Prunable(Protocol):
    """A protocol that defines a prunable object.

    This protocol is used to define objects that can be purged from memory or storage.
    """

    async def purge(  # noqa: D102, PLR0913
        self,
        *,
        limit: int | None = 100,
        check: Callable[[Message], bool] = MISSING,
        before: SnowflakeTime | None = None,
        after: SnowflakeTime | None = None,
        around: SnowflakeTime | None = None,
        oldest_first: bool | None = None,
        bulk: bool = True,
        reason: str | None = None,
    ) -> list[Message]: ...


@runtime_checkable
class History(Protocol):
    """A protocol that defines a object with history."""

    def history(  # noqa: D102
        self,
        *,
        limit: int | None = 100,
        before: SnowflakeTime | None = None,
        after: SnowflakeTime | None = None,
        around: SnowflakeTime | None = None,
        oldest_first: bool | None = None,
    ) -> AsyncIterator[Message]: ...


@runtime_checkable
class PrunableHistory(Prunable, History):
    """A protocol that defines a prunable channel with history."""


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
class Purge(Cog, auto_load=True):
    """A cog that provides a command to purge messages."""

    limit = Config(100)
    allow_history = Config(default=False)

    @app_commands.command(name="purge", description="Purge X amount of messages, use history to delete older messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def slash_purge(
        self,
        interaction: discord.Interaction,
        count: int,
        *,
        use_history: bool = False,
    ) -> None:
        """Purge X amount of messages, use history to delete older messages."""
        if count == -1:
            count = self.limit

        if count > self.limit:
            await interaction.response.send_message(
                f"Too many message to kill! The limit is {self.limit}",
                ephemeral=True,
            )
            return
        await self._purge(interaction, count, use_history=use_history)

    async def _purge(self, interaction: Interaction, count: int, *, use_history: bool) -> None:
        # NoteL Using history will be lots slower, and will cause rate limit (aka, it'll slow down.)
        await interaction.response.defer()
        history_messages_count = 0
        purged_count = 0

        if not isinstance(interaction.channel, Prunable):
            await interaction.followup.send(
                "This channel cannot be purged.",
                ephemeral=True,
            )
            return

        purged = await interaction.channel.purge(limit=count)
        purged_count = len(purged)
        self.logger.debug(f"Purged: {purged_count}")
        # fmt: off
        if (
            purged_count < count
            and self.allow_history
            and use_history
            and isinstance(interaction.channel, PrunableHistory)
        ):
        # fmt: on
            history_messages = await self.history_delete(interaction.channel, count=(count - purged_count))
            history_messages_count = len(history_messages)
            self.logger.debug(f"History killed: {history_messages_count}")
        await interaction.followup.send(f"{interaction.user.mention} Killed {history_messages_count + purged_count} Messages")

    async def history_delete(self, channel: PrunableHistory, count: int) -> list[discord.Message]:
        """Delete messages from the channel history. Rather than messages in cache. (Older messages)."""
        messages = []

        async for message in channel.history(limit=count):
            message: discord.Message
            with contextlib.suppress(discord.NotFound):
                await message.delete()
            messages.append(message)
        return messages
