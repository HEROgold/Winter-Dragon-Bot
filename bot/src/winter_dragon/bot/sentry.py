import sentry_sdk

from bot.src.winter_dragon.bot.config import Config


class Sentry:
    """A class to handle Sentry setup."""

    dsn = Config("")


    def __init__(self) -> None:
        """Initialize Sentry."""
        sentry_sdk.init(
            dsn=self.dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
