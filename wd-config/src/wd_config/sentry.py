"""Configurable Sentry settings, backed by their own sentry.ini file."""

from __future__ import annotations

lazy import enum
lazy from enum import auto

lazy from confkit import Enum

lazy from .config import Config
lazy from .constants import SENTRY_CONFIG_FILE
lazy from .parser import REQUIRED


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

    @classmethod
    def resolved_dsn(cls) -> str | None:
        """Return the DSN to pass to ``sentry_sdk.init``: ``None`` while it's empty or still :data:`REQUIRED`."""
        dsn = cls.dsn
        return None if dsn in {"", REQUIRED} else dsn
