"""Module to handle Sentry setup."""

from configparser import ConfigParser
from pathlib import Path

import sentry_sdk
from confkit import Config


if not Config._parser: # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    Config.set_parser(ConfigParser())
Config.set_file(Path(__file__).parent / "sentry_config.ini")

class Sentry:
    """A class to handle Sentry setup."""

    Telemetry = Config(default=True)
    dsn = Config("")
    environment = Config("development")


    def __init__(self) -> None:
        """Initialize Sentry."""
        sentry_sdk.init(
            environment=self.environment,
            dsn=self.dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            _experiments={
                "enable_logs": True,
            },
            traces_sample_rate=1, # 100% of error traces will be sent
        )
