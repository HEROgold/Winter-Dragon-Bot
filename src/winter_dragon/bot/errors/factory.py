"""Module for creating Error errors from Error log entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast


if TYPE_CHECKING:
    from collections.abc import Generator

    from discord import Interaction
    from discord.app_commands.errors import AppCommandError
    from discord.ext.commands import CommandError, Context
    from discord.ext.commands.bot import BotBase

    from winter_dragon.bot.core.bot import BotT

    from .alias import DiscordCommandError
    from .error import DiscordError


class ErrorFactory:
    """Factory for creating Error errors."""

    registry: ClassVar[dict[DiscordCommandError, list[type[DiscordError]]]] = {}

    @classmethod
    def register(cls, error: DiscordCommandError, error_type: type[DiscordError]) -> None:
        """Register an Error error class for a category."""
        if error not in cls.registry:
            cls.registry[error] = [error_type]
            return
        cls.registry[error] += [error_type]

    @classmethod
    def get_handlers(
        cls,
        bot: BotBase,
        error_type: DiscordCommandError,
        *,
        interaction: Interaction | None = None,
        ctx: Context[BotT] | None = None,
    ) -> Generator[DiscordError]:
        """Get the Error error class for a category."""
        if error_type not in cls.registry:
            msg = f"Error for `{error_type}` not implemented"
            raise NotImplementedError(msg)
        if not (interaction or ctx):
            msg = "Missing interaction or ctx kwarg"
            raise ValueError(msg)
        if interaction and ctx:
            msg = "Cannot pass both interaction and ctx"
            raise ValueError(msg)

        for handler in cls.registry[error_type]:
            if interaction:
                error_type = cast("AppCommandError", error_type)
                yield handler(bot, interaction, error_type)
            elif ctx:
                error_type = cast("CommandError", error_type)
                yield handler(bot, ctx, error_type)
