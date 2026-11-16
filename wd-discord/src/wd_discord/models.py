"""Shared pydantic base for all Discord API response models.

Every object parsed from a Discord REST/gateway response subclasses :class:`DiscordModel`,
which validates the payload through pydantic v2. Unknown/undocumented keys are captured in
``model_extra`` (``extra="allow"``) and logged as warnings (the logging integration forwards
those to Sentry as logs, not error events, so they never use the error quota) so new Discord fields surface
instead of being silently dropped.
"""

lazy from typing import TYPE_CHECKING, Self

lazy from pydantic import BaseModel, ConfigDict, model_validator

lazy from wd_discord.log import get_logger


if TYPE_CHECKING:
    lazy from collections.abc import Mapping


logger = get_logger("DiscordModel")
_logged: set[tuple[str, frozenset[str]]] = set()
"""The (model, field names) pairs already logged, so each is logged once per process."""


def _report_unknown_fields(model_name: str, extra: Mapping[str, object]) -> None:
    """Log undocumented Discord fields as a warning, which Sentry receives as a log and not as an error event.

    Logs the unknown keys locally once per model and set of field names (a GUILD_CREATE alone carries
    hundreds of the same users and channels), so the log shows each new field without drowning in it.
    """
    if (key := (model_name, frozenset(extra))) not in _logged:
        _logged.add(key)
        logger.warning(t"unknown fields on {model_name}: {extra}")


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
        """Log any undocumented keys captured in ``model_extra``."""
        if self.model_extra:
            _report_unknown_fields(type(self).__name__, self.model_extra)
        return self
