"""Module for creating Error errors from Error log entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast


if TYPE_CHECKING:
    from collections.abc import Generator

    from discord import DiscordException, Interaction
    from discord.app_commands.errors import AppCommandError
    from discord.ext.commands import CommandError, Context
    from discord.ext.commands.bot import BotBase

    from winter_dragon.bot.core.bot import BotT

    from .error import DiscordError


class ErrorFactory:
    """Factory for creating Error errors."""

    registry: ClassVar[dict[type[DiscordException], list[type[DiscordError]]]] = {}

    @classmethod
    def register(cls, error: type[DiscordException], error_type: type[DiscordError]) -> None:
        """Register an Error error class for a category."""
        if error not in cls.registry:
            cls.registry[error] = [error_type]
            return
        cls.registry[error] += [error_type]

    @classmethod
    def get_handlers(
        cls,
        bot: BotBase,
        exception: DiscordException,
        *,
        interaction: Interaction | None = None,
        ctx: Context[BotT] | None = None,
    ) -> Generator[DiscordError]:
        """Get the Error error class for a category."""
        exc_type = type(exception)
        if exc_type not in cls.registry:
            msg = f"Error for `{exc_type}` not implemented"
            raise NotImplementedError(msg)
        if not (interaction or ctx):
            msg = "Missing interaction or ctx kwarg"
            raise ValueError(msg)
        if interaction and ctx:
            msg = "Cannot pass both interaction and ctx"
            raise ValueError(msg)

        for handler in cls.registry[exc_type]:
            if interaction:
                exc_type = cast("AppCommandError", exc_type)
                yield handler(bot, interaction, exc_type)
            elif ctx:
                exc_type = cast("CommandError", exc_type)
                yield handler(bot, ctx, exc_type)
