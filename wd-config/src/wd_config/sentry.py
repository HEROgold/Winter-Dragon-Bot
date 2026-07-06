"""Configurable Sentry settings."""

from __future__ import annotations

import enum
from enum import auto

from confkit import Enum

from .config import Config


class Environments(enum.StrEnum):
    """Enum for different environments."""

    development = auto()
    production = auto()
    staging = auto()


class SentrySettings:
    """Configurable Sentry settings."""

    Telemetry = Config(default=True)
    dsn = Config("")
    environment = Config(Enum(Environments.development))
