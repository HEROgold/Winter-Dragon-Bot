"""Enums for values Discord owns, which accept a value Discord adds later instead of refusing the payload.

Discord adds enum values without notice (a nameplate palette, a channel type, a guild feature). A plain enum
refuses them, and a payload that fails validation is a lost event. :class:`OpenIntEnum` and :class:`OpenStrEnum`
turn an unknown value of the right type into a member of its own (``ChannelType.UNKNOWN_99``,
``GuildFeature.NEW_FEATURE``), report it once so the enum can be updated, and refuse values of the wrong type.
Enums of values this code sends or owns stay plain enums.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
lazy from typing import Self, cast, override

lazy import sentry_sdk
lazy from herogold.log import getLogger
lazy from wd_config.sentry import SentrySettings


_reported: set[tuple[str, object]] = set()


class OpenIntEnum(IntEnum):
    """An IntEnum of Discord's values: an unknown int becomes a member named ``UNKNOWN_<value>``."""

    @override
    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        """Make an unknown int a member; refuse anything else."""
        if not isinstance(value, int) or isinstance(value, bool):
            return None
        member = int.__new__(cls, value)
        member._name_ = f"UNKNOWN_{value}"
        member._value_ = value
        _report(cls.__name__, value)
        return cast("Self", cls._value2member_map_.setdefault(value, member))


class OpenStrEnum(StrEnum):
    """A StrEnum of Discord's values: an unknown string becomes a member named after it."""

    @override
    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        """Make an unknown string a member; refuse anything else."""
        if not isinstance(value, str):
            return None
        member = str.__new__(cls, value)
        member._name_ = value.upper()
        member._value_ = value
        _report(cls.__name__, value)
        return cast("Self", cls._value2member_map_.setdefault(value, member))


def _report(enum: str, value: object) -> None:
    """Log an unknown value once per process, and send it to Sentry when telemetry is on."""
    if (enum, value) in _reported:
        return
    _reported.add((enum, value))
    getLogger("DiscordModel").warning(t"unknown value of {enum}: {value!r}")
    if SentrySettings.Telemetry:
        sentry_sdk.capture_message(
            f"wd-discord: unknown value of {enum}: {value!r}",
            level="warning",
            fingerprint=["wd-discord-unknown-enum-value", enum, repr(value)],
        )
