"""Configurable Sentry settings, backed by their own sentry.ini file."""

lazy import enum
lazy from enum import auto

lazy from confkit import Enum

lazy from .config import Config
lazy from .constants import SENTRY_CONFIG_FILE
lazy from .parser import REQUIRED, is_required


class SentryConfig[T](Config[T]):
    """Config descriptor scoped to the Sentry settings file."""


SentryConfig.bind(SENTRY_CONFIG_FILE, operator=True)


class Environments(enum.StrEnum):
    """Enum for different environments."""

    development = auto()
    production = auto()
    staging = auto()
    test = auto()


class SentrySettings:
    """Configurable Sentry settings."""

    Telemetry = SentryConfig(default=True)
    dsn = SentryConfig(REQUIRED)
    """The project DSN; the operator fills it in."""
    environment = SentryConfig(Enum(Environments.development))
    traces_sample_rate = SentryConfig(1.0)
    """The share of interactions and periodic ticks traced, from 0 (none) to 1 (all)."""
    listener_traces_sample_rate = SentryConfig(0.05)
    """The share of listener calls traced; lower, since some gateway events arrive many times a second."""
    profile_session_sample_rate = SentryConfig(0.0)
    """The share of processes that profile their traced transactions, from 0 (off) to 1. Sentry bills profiling
    separately, so it stays off until someone turns it on to find what's slow."""

    @classmethod
    def resolved_dsn(cls) -> str | None:
        """Return the DSN to pass to ``sentry_sdk.init``: ``None`` while it's empty or still :data:`REQUIRED`."""
        dsn = cls.dsn
        return None if not dsn or is_required(dsn) else dsn
