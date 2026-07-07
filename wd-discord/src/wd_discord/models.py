"""Shared pydantic base for all Discord API response models.

Every object parsed from a Discord REST/gateway response subclasses :class:`DiscordModel`,
which validates the payload through pydantic v2. Unknown/undocumented keys are captured in
``model_extra`` (``extra="allow"``) and reported to Sentry - gated by
:attr:`~wd_config.sentry.SentrySettings.Telemetry` - so new Discord fields surface as telemetry
instead of being silently dropped.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Self

import sentry_sdk
from pydantic import BaseModel, ConfigDict, model_validator
from wd_config.sentry import SentrySettings


if TYPE_CHECKING:
    from collections.abc import Mapping


def _report_unknown_fields(model_name: str, extra: Mapping[str, object]) -> None:
    """Report undocumented Discord fields to Sentry when telemetry is enabled.

    A no-op when ``sentry_sdk.init`` has not run, and never raises: telemetry must not turn a
    successful response parse into a failure.
    """
    if not SentrySettings.Telemetry:
        return
    try:
        sentry_sdk.capture_message(
            f"wd-discord: unknown fields on {model_name}: {extra}",
            level="warning",
        )
    except Exception:  # noqa: BLE001 - telemetry is best-effort; a broken reporter must not break parsing
        return


class DiscordModel(BaseModel):
    """Base for every Discord API response model.

    ``extra="allow"`` keeps unknown keys (a transport layer must survive Discord shipping new
    fields) so :meth:`_report_unknown_fields` can surface them rather than dropping them.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
        frozen=False,
    )

    @model_validator(mode="after")
    def _check_unknown_fields(self) -> Self:
        """Report any undocumented keys captured in ``model_extra`` to Sentry."""
        if self.model_extra:
            _report_unknown_fields(type(self).__name__, self.model_extra)
        return self
