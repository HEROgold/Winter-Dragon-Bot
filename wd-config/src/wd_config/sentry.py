"""Configurable Sentry settings."""

from __future__ import annotations

lazy import enum
lazy from enum import auto

lazy from confkit import Enum

lazy from .config import Config


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
