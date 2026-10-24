"""Refusing an action: stop a command, button or listener and tell the user why.

Cog and domain code raises :class:`Refused` when it can't go ahead, instead of answering and returning by hand;
wd-bot answers the interaction with the message, privately. :func:`unwrap` turns a failed wd-discord call
(``T | NetworkError``) into a refusal, so a call site stays one line::

    channel = unwrap(await interaction.channel.fetch(), "I couldn't read this channel.")
"""

lazy from typing import TYPE_CHECKING

lazy from wd_discord import is_network_error

lazy from .base import BaseError


if TYPE_CHECKING:
    lazy from wd_discord import NetworkError


class Refused(BaseError):  # noqa: N818 - reads as the outcome: the action was refused
    """An action that can't go ahead; :attr:`message` tells the user who asked why."""

    def __init__(self, message: str, *, cause: NetworkError | None = None) -> None:
        """Refuse with ``message``; ``cause`` is the failed Discord call behind it, kept for the log."""
        super().__init__(message)
        self.message = message
        self.cause = cause


def unwrap[T](result: T | NetworkError, message: str) -> T:
    """Return ``result``, or refuse with ``message`` when it's a failed Discord call."""
    if is_network_error(result):
        raise Refused(message, cause=result)
    return result
