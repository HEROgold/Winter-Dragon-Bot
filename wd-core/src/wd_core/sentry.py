"""Module to handle Sentry setup."""

from __future__ import annotations

import sentry_sdk
from wd_config.sentry import SentrySettings


class Sentry:
    """A class to handle Sentry setup."""

    def __init__(self) -> None:
        """Initialize Sentry."""
        sentry_sdk.init(
            environment=SentrySettings.environment.value,
            dsn=SentrySettings.dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
            _experiments={
                "enable_logs": True,
            },
            traces_sample_rate=1,  # 100% of error traces will be sent
        )
