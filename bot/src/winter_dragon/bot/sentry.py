"""Module to handle Sentry setup."""

import sentry_sdk
from winter_dragon.bot.config import Config


class Sentry:
    """A class to handle Sentry setup."""

    dsn = Config("", str)


    def __init__(self) -> None:
        """Initialize Sentry."""
        sentry_sdk.init(
            dsn=self.dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            _experiments={
                "enable_logs": True,
            },
            traces_sample_rate=1, # 100% of error traces will be sent
        )
