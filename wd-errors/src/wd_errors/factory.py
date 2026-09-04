"""Module for creating Error errors lazy from Error log entries."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, ClassVar, cast

lazy from herogold.log import getLogger


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from wd_types.alias import Bot

    lazy from .error import DiscordError


class ErrorFactory:
    """Factory for creating Error errors."""

    registry: ClassVar[dict[type[DiscordException], list[type[DiscordError]]]] = {}
    logger: ClassVar = getLogger("ErrorFactory")

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
        ctx: Context[Bot] | None = None,
    ) -> Generator[DiscordError]:
        """Get the Error error class for a category."""
        exc_type = type(exception)
        if exc_type not in cls.registry:
            msg = t"Error for `{exc_type}` not implemented"
            cls.logger.critical(msg)
            raise NotImplementedError(msg)
        if not (interaction or ctx):
            msg = t"Missing interaction or ctx kwarg {exc_type=}"
            cls.logger.critical(msg)
            raise ValueError(msg)
        if interaction and ctx:
            msg = t"Cannot pass both interaction and ctx {exc_type=}"
            cls.logger.critical(msg)
            raise ValueError(msg)

        for handler in cls.registry[exc_type]:
            if interaction:
                exc_type = cast("AppCommandError", exc_type)
                yield handler(bot, interaction, exc_type)
            elif ctx:
                exc_type = cast("CommandError", exc_type)
                yield handler(bot, ctx, exc_type)
