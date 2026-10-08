"""Message-component handlers: route a clicked component to the Cog method owning its ``custom_id`` prefix.

A ``custom_id`` is ``<prefix>:<arg>:<arg>...``. The prefix picks the handler and the args travel with the
component, so a handler rebuilds whatever it needs from them and keeps working across restarts and on old messages.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Self

lazy from herogold.log import LoggerMixin
lazy from wd_discord.components import MAX_CUSTOM_ID_LENGTH


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Sequence

    lazy from wd_discord import ComponentInteraction

    lazy from wd_bot.cogs import Cog


CUSTOM_ID_SEPARATOR = ":"


def parse_custom_id(custom_id: str) -> tuple[str, list[str]]:
    """Split ``custom_id`` into its handler prefix and the args after it."""
    prefix, *args = custom_id.split(CUSTOM_ID_SEPARATOR)
    return prefix, args


class ComponentHandler(LoggerMixin):
    """A Cog method handling every component whose ``custom_id`` starts with :attr:`prefix`.

    Built by :meth:`wd_bot.cogs.Cog.component`. The handler is called as ``func(cog, interaction, *args)`` with
    the ``custom_id``'s args as strings, and must answer the interaction within Discord's 3-second window.
    """

    def __init__(self, func: Callable[..., Awaitable[None]], *, prefix: str) -> None:
        """Wrap ``func`` as the handler for ``prefix``."""
        if not prefix or CUSTOM_ID_SEPARATOR in prefix:
            msg = f"Component prefix must be non-empty and contain no {CUSTOM_ID_SEPARATOR!r}, got {prefix!r}"
            raise ValueError(msg)
        self.func = func
        self.prefix = prefix

    def custom_id(self, *args: str | int) -> str:
        """Build a ``custom_id`` routed to this handler, carrying ``args``.

        Raises :class:`ValueError` if an arg contains the separator or the result exceeds Discord's 100 characters.
        """
        parts = [str(arg) for arg in args]
        if any(CUSTOM_ID_SEPARATOR in part for part in parts):
            msg = f"custom_id args must not contain {CUSTOM_ID_SEPARATOR!r}, got {parts}"
            raise ValueError(msg)
        custom_id = CUSTOM_ID_SEPARATOR.join((self.prefix, *parts))
        if len(custom_id) > MAX_CUSTOM_ID_LENGTH:
            msg = f"custom_id is {len(custom_id)} characters, Discord allows {MAX_CUSTOM_ID_LENGTH}: {custom_id!r}"
            raise ValueError(msg)
        return custom_id

    async def invoke(self, cog: Cog, interaction: ComponentInteraction, args: Sequence[str]) -> bool:
        """Call the handler; return ``False`` if it raised (the exception is logged)."""
        try:
            await self.func(cog, interaction, *args)
        except Exception:
            self.logger.exception(t"Unhandled exception in component handler '{self.prefix}'")
            return False
        return True

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow access as a plain attribute on a Cog instance without binding it like a method."""
        return self
