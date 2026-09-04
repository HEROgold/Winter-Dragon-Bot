"""Module to handle Sentry setup for wd-discord.

Mirrors :mod:`wd_core.sentry` so the client library can initialize Sentry independently of the
bot runtime, using the same :class:`~wd_config.sentry.SentrySettings` config and scope. Once
:class:`Sentry` is constructed, the unknown-field telemetry in :mod:`wd_discord.models` starts
delivering events instead of being a no-op.
"""

from __future__ import annotations

lazy import sentry_sdk
lazy from wd_config.sentry import SentrySettings


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
