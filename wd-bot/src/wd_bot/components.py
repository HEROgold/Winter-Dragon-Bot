"""Message-component handlers: route a clicked component to the Cog method owning its ``custom_id`` prefix.

A ``custom_id`` is ``<prefix>:<arg>:<arg>...``. The prefix picks the handler and the args travel with the
component, so a handler rebuilds whatever it needs from them and keeps working across restarts and on old messages.
"""

lazy from typing import TYPE_CHECKING, ClassVar, Self, override

lazy from herogold.log import LoggerMixin
lazy from wd_discord import ComponentInteraction, ModalSubmitInteraction
lazy from wd_discord.limits import MAX_CUSTOM_ID_LENGTH

lazy from wd_bot.checks import require_guild
lazy from wd_bot.commands import wants_guild_interaction
lazy from wd_bot.guard import dispatch_guard


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Sequence

    lazy from wd_discord.snowflake import Snowflake

    lazy from wd_bot.cogs import Cog


CUSTOM_ID_SEPARATOR = ":"


def parse_custom_id(custom_id: str) -> tuple[str, list[str]]:
    """Split ``custom_id`` into its handler prefix and the args after it."""
    prefix, *args = custom_id.split(CUSTOM_ID_SEPARATOR)
    return prefix, args


class CustomIdHandler[I: ComponentInteraction | ModalSubmitInteraction](LoggerMixin):
    """A Cog method reached through the prefix of a ``custom_id``: what component and modal handlers share."""

    kind: ClassVar[str]
    """What the handler is called in logs: ``component`` or ``modal``."""

    def __init__(self, func: Callable[..., Awaitable[None]], *, prefix: str) -> None:
        """Wrap ``func`` as the handler for ``prefix``."""
        if not prefix or CUSTOM_ID_SEPARATOR in prefix:
            msg = f"Component prefix must be non-empty and contain no {CUSTOM_ID_SEPARATOR!r}, got {prefix!r}"
            raise ValueError(msg)
        self.func = func
        self.prefix = prefix
        self.wants_guild = wants_guild_interaction(func)
        """Whether the handler's ``interaction`` is annotated as a guild interaction; its cog must then be guild-only."""

    def custom_id(self, *args: str | int | Snowflake) -> str:
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

    def __get__(self, instance: object, owner: type) -> Self:
        """Allow access as a plain attribute on a Cog instance without binding it like a method."""
        return self

    def _prepare(self, cog: Cog, interaction: I) -> I:  # noqa: ARG002 - subclasses use the cog
        """Return the interaction as the handler receives it; a subclass may check or narrow it."""
        return interaction

    async def invoke(self, cog: Cog, interaction: I, args: Sequence[str]) -> bool:
        """Call the handler through :data:`~wd_bot.guard.dispatch_guard`; return ``False`` if it raised."""

        async def call() -> None:
            await self.func(cog, self._prepare(cog, interaction), *args)

        return await dispatch_guard.run(f"{self.kind} '{self.prefix}'", call, interaction)


class ComponentHandler(CustomIdHandler[ComponentInteraction]):
    """A Cog method handling every component whose ``custom_id`` starts with :attr:`prefix`.

    Built by :meth:`wd_bot.cogs.Cog.component`. The handler is called as ``func(cog, interaction, *args)`` with
    the ``custom_id``'s args as strings, and must answer the interaction within Discord's 3-second window.
    """

    kind = "component"

    @override
    def _prepare(self, cog: Cog, interaction: ComponentInteraction) -> ComponentInteraction:
        return require_guild(interaction) if type(cog).guild_only() else interaction


class ModalHandler(CustomIdHandler[ModalSubmitInteraction]):
    """A Cog method handling every modal whose ``custom_id`` starts with :attr:`prefix`.

    Built by :meth:`wd_bot.cogs.Cog.modal`. The handler is called as ``func(cog, interaction, *args)`` with the
    ``custom_id``'s args as strings (build one with :meth:`custom_id`, to pass to ``show_modal``), and must answer
    the interaction within Discord's 3-second window. The typed values are in ``interaction.values``.
    """

    kind = "modal"
