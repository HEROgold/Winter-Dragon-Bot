"""Shared pydantic base for all Discord API response models.

Every object parsed from a Discord REST/gateway response subclasses :class:`DiscordModel`,
which validates the payload through pydantic v2. Unknown/undocumented keys are captured in
``model_extra`` (``extra="allow"``) and reported to Sentry - gated by
:attr:`~wd_config.sentry.SentrySettings.Telemetry` - so new Discord fields surface as telemetry
instead of being silently dropped.
"""

lazy from typing import TYPE_CHECKING, Self

lazy import sentry_sdk
lazy from pydantic import BaseModel, ConfigDict, model_validator
lazy from wd_config.sentry import SentrySettings

lazy from wd_discord.log import get_logger


if TYPE_CHECKING:
    lazy from collections.abc import Mapping


logger = get_logger("DiscordModel")
_logged: set[tuple[str, frozenset[str]]] = set()
"""The (model, field names) pairs already logged, so each is logged once per process."""


def _report_unknown_fields(model_name: str, extra: Mapping[str, object]) -> None:
    """Report undocumented Discord fields to Sentry when telemetry is enabled.

    Logs the unknown keys locally once per model and set of field names (a GUILD_CREATE alone carries
    hundreds of the same users and channels), so the log shows each new field without drowning in it.
    The Sentry ``capture_message`` is a no-op when ``sentry_sdk.init`` has not run, and never raises:
    telemetry must not turn a successful response parse into a failure.

    The Sentry message and fingerprint name only the model and the field names, so one new field is one
    Sentry issue however its values vary; the values ride along as the event's ``unknown_fields`` context.
    """
    if (key := (model_name, frozenset(extra))) not in _logged:
        _logged.add(key)
        logger.warning(t"unknown fields on {model_name}: {extra}")
    if not SentrySettings.Telemetry:
        return
    fields = sorted(extra)
    try:
        sentry_sdk.capture_message(
            f"wd-discord: unknown fields on {model_name}: {', '.join(fields)}",
            level="warning",
            fingerprint=["wd-discord-unknown-fields", model_name, *fields],
            contexts={"unknown_fields": {key: repr(value) for key, value in extra.items()}},
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
