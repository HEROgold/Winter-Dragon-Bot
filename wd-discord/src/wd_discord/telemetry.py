"""Timings and counts the client and the bot report, for a metrics exporter to subscribe to.

wd-discord exports nothing itself: :func:`~wd_discord.sentry.transaction` reports how long each interaction, listener
call and periodic tick took, :meth:`Client._send <wd_discord.client.Client._send>` each REST call, and the bot each
gateway event it received. The app's Prometheus exporter (:mod:`winter_dragon.metrics`) subscribes to them.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, ClassVar


if TYPE_CHECKING:
    lazy from collections.abc import Callable


REST = "http.client"
"""The :attr:`Timing.kind` of a REST call."""


@dataclass(frozen=True, slots=True)
class Timing:
    """How long one piece of work took."""

    kind: str
    """A :class:`~wd_discord.sentry.TraceOp`, or :data:`REST`."""
    name: str
    """What ran, without IDs or user input: ``/stats reset``, ``GET /channels/{channel_id}``."""
    seconds: float
    outcome: str
    """``ok`` or ``error``; for a REST call, the HTTP status code."""


class Telemetry:
    """The subscribers to what the client and the bot report; a subscriber must be quick and must not raise."""

    timing_observers: ClassVar[list[Callable[[Timing], None]]] = []
    event_observers: ClassVar[list[Callable[[str], None]]] = []

    @classmethod
    def subscribe(
        cls,
        *,
        timings: Callable[[Timing], None] | None = None,
        events: Callable[[str], None] | None = None,
    ) -> None:
        """Call ``timings`` with each :class:`Timing` reported, and ``events`` with each gateway event's name."""
        if timings is not None:
            cls.timing_observers.append(timings)
        if events is not None:
            cls.event_observers.append(events)

    @classmethod
    def unsubscribe_all(cls) -> None:
        """Drop every subscriber."""
        cls.timing_observers.clear()
        cls.event_observers.clear()

    @classmethod
    def timing(cls, timing: Timing) -> None:
        """Report ``timing`` to every subscriber."""
        for observe in cls.timing_observers:
            observe(timing)

    @classmethod
    def event(cls, name: str) -> None:
        """Report that the gateway event ``name`` arrived."""
        for observe in cls.event_observers:
            observe(name)
