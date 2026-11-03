"""Sentry setup for the bot, the web dashboard and the client library, and the transactions the bot traces.

Reads :class:`~wd_config.sentry.SentrySettings`. Once :class:`Sentry` is constructed, the
unknown-field telemetry in :mod:`wd_discord.models` starts delivering events instead of being a no-op, and
:func:`transaction` starts sending traces.

Each interaction, listener call and periodic tick is one transaction (:class:`TraceOp`). Inside one, every REST call
is an ``http.client`` span named by its route shape (:meth:`Client._send <wd_discord.client.Client._send>`) and every
database query a ``db`` span (Sentry's SQLAlchemy integration, on by default). Sentry's httpx integrations stay off:
they would name each call by its full URL, interaction tokens included.

With :attr:`~wd_config.sentry.SentrySettings.profile_session_sample_rate` above 0, sampled transactions are profiled.
"""

lazy import enum
lazy import time
lazy from contextlib import contextmanager
lazy from importlib import import_module
lazy from typing import TYPE_CHECKING, Any

lazy import sentry_sdk
lazy from sentry_sdk.integrations import DidNotEnable
lazy from wd_config.sentry import SentrySettings

lazy from wd_discord.telemetry import Telemetry, Timing


if TYPE_CHECKING:
    lazy from collections.abc import Generator

    lazy from sentry_sdk.integrations import Integration
    lazy from sentry_sdk.tracing import Span


HTTPX_INTEGRATIONS = (
    ("sentry_sdk.integrations.httpx", "HttpxIntegration"),
    ("sentry_sdk.integrations.httpx2", "Httpx2Integration"),
)
"""Sentry's integrations for httpx, which httpxyz registers itself as; :class:`Sentry` keeps them off."""


class TraceOp(enum.StrEnum):
    """What a transaction traces; Sentry groups and samples transactions by it."""

    INTERACTION = "discord.interaction"
    """A command, autocomplete, component or modal interaction, named after what it ran."""
    LISTENER = "discord.listener"
    """One listener's call for one gateway event; sampled at its own, lower rate."""
    PERIODIC = "task.periodic"
    """One tick of a cog's periodic task."""


def traces_sampler(context: dict[str, Any]) -> float:
    """Return the share of transactions like ``context`` to send: listeners at their own rate, the rest at the main one.

    A transaction continuing a sampled (or dropped) trace follows it.
    """
    parent = context.get("parent_sampled")
    if parent is not None:
        return float(parent)
    op = context.get("transaction_context", {}).get("op")
    if op == TraceOp.LISTENER:
        return SentrySettings.listener_traces_sample_rate
    return SentrySettings.traces_sample_rate


def httpx_integrations() -> Generator[Integration]:
    """Yield each of :data:`HTTPX_INTEGRATIONS` that can load; one that can't wouldn't be enabled anyway."""
    for module, name in HTTPX_INTEGRATIONS:
        try:
            yield getattr(import_module(module), name)()
        except ImportError, DidNotEnable:
            continue


@contextmanager
def transaction(op: TraceOp, name: str) -> Generator[Span]:
    """Trace the block as one ``op`` transaction named ``name``, in a scope of its own.

    The bot runs each interaction, listener and tick in its own task; the isolation scope keeps the tags one sets from
    leaking into the next. How long it took goes to :class:`~wd_discord.telemetry.Telemetry` too, ``error`` when the
    block raised.
    """
    start = time.perf_counter()
    outcome = "error"
    try:
        with sentry_sdk.isolation_scope(), sentry_sdk.start_transaction(op=op, name=name, source="task") as traced:
            yield traced
        outcome = "ok"
    finally:
        Telemetry.timing(Timing(kind=op, name=name, seconds=time.perf_counter() - start, outcome=outcome))


class Sentry:
    """A class to handle Sentry setup."""

    def __init__(self) -> None:
        """Initialize Sentry."""
        sentry_sdk.init(
            environment=SentrySettings.environment.value,
            dsn=SentrySettings.resolved_dsn(),
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            _experiments={
                "enable_logs": True,
            },
            traces_sampler=traces_sampler,
            # Profile only while a sampled transaction runs, in the share of processes sentry.ini asks for (none by
            # default): docs/dev/observability.md says when to turn it on.
            profile_session_sample_rate=SentrySettings.profile_session_sample_rate,
            profile_lifecycle="trace",
            # httpxyz is httpx underneath, so these would trace each REST call again under its full URL, interaction
            # tokens included. Client._send traces it under its route shape instead.
            disabled_integrations=list(httpx_integrations()),
        )
        sentry_sdk.set_user({"ip_address": "{{auto}}"})
