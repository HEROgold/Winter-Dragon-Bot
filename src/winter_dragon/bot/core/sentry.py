"""Module to handle Sentry setup."""

import enum
from enum import auto

import sentry_sdk
from confkit import Enum

from .config import Config


class Environments(enum.StrEnum):
    """Enum for different environments."""

    development = auto()
    production = auto()
    staging = auto()


class Sentry:
    """A class to handle Sentry setup."""

    Telemetry = Config(default=True)
    dsn = Config("")
    environment = Config(Enum(Environments.development))

    def __init__(self) -> None:
        """Initialize Sentry."""
        sentry_sdk.init(
            environment=self.environment.value,
            dsn=self.dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            _experiments={
                "enable_logs": True,
            },
            traces_sample_rate=1,  # 100% of error traces will be sent
        )
