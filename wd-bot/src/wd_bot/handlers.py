"""Which cog methods handle gateway events, component clicks and modal submits: the counterpart of the command registry."""

lazy import inspect
lazy from typing import TYPE_CHECKING

lazy from herogold.log import LoggerMixin


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Iterable, Sequence

    lazy from wd_discord import ComponentInteraction, ModalSubmitInteraction

    lazy from wd_bot.cogs import Cog
    lazy from wd_bot.components import CustomIdHandler

    type Listener = Callable[..., Awaitable[None]]


class HandlerRegistry(LoggerMixin):
    """The ``@Cog.listener`` methods per gateway event, and the ``@Cog.component`` and ``@Cog.modal`` handler per prefix.

    A dict keyed by a runtime event name can't track which payload type belongs to which key; the payload type is
    checked where the listener is declared, by ``listener.pyi``'s overloads.
    """

    def __init__(self) -> None:
        """Start empty."""
        self._listeners: dict[str, list[Listener]] = {}
        self._components: dict[str, tuple[Cog, CustomIdHandler[ComponentInteraction]]] = {}
        self._modals: dict[str, tuple[Cog, CustomIdHandler[ModalSubmitInteraction]]] = {}

    def register(self, cog: Cog) -> None:
        """Add ``cog``'s listeners, component handlers and modal handlers.

        A prefix another cog already registered is taken over by ``cog``, with a warning.
        """
        for _, member in inspect.getmembers(cog, predicate=inspect.iscoroutinefunction):
            if event := getattr(member, "__listener_event__", None):
                self._listeners.setdefault(event, []).append(member)
        self._register_custom_ids(cog, type(cog).components(), self._components)
        self._register_custom_ids(cog, type(cog).modals(), self._modals)

    def _register_custom_ids[I: ComponentInteraction | ModalSubmitInteraction](
        self,
        cog: Cog,
        handlers: Iterable[CustomIdHandler[I]],
        registry: dict[str, tuple[Cog, CustomIdHandler[I]]],
    ) -> None:
        """Route each handler's prefix in ``registry`` to ``cog``, warning when that replaces another cog's handler."""
        for handler in handlers:
            if (existing := registry.get(handler.prefix)) is not None and existing[0] is not cog:
                previous = existing[0].__cog_name__
                self.logger.warning(
                    t"Duplicate {handler.kind} prefix '{handler.prefix}': cog '{cog.__cog_name__}' replaces '{previous}'",
                )
            registry[handler.prefix] = (cog, handler)

    def unregister(self, cog: Cog) -> None:
        """Remove ``cog``'s listeners, component handlers and modal handlers."""
        for listeners in self._listeners.values():
            listeners[:] = [listener for listener in listeners if getattr(listener, "__self__", None) is not cog]
        for registry in (self._components, self._modals):
            for prefix in [prefix for prefix, (owner, _) in registry.items() if owner is cog]:
                del registry[prefix]

    def listeners(self, event_name: str) -> Sequence[Listener]:
        """Return the bound listener methods for the gateway event ``event_name``, in registration order."""
        return tuple(self._listeners.get(event_name, ()))

    def component(self, prefix: str) -> tuple[Cog, CustomIdHandler[ComponentInteraction]] | None:
        """Return the cog and component handler owning the ``custom_id`` prefix ``prefix``, or ``None`` if none does."""
        return self._components.get(prefix)

    def modal(self, prefix: str) -> tuple[Cog, CustomIdHandler[ModalSubmitInteraction]] | None:
        """Return the cog and modal handler owning the ``custom_id`` prefix ``prefix``, or ``None`` if none does."""
        return self._modals.get(prefix)
