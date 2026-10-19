"""Tests for wd_discord.timestamp: Discord timestamp markup."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from wd_discord.timestamp import DiscordTime, TimestampStyle


MOMENT = datetime(2021, 4, 20, 16, 20, 30, tzinfo=UTC)
EPOCH = 1618935630


def test_epoch_is_whole_seconds() -> None:
    assert DiscordTime(MOMENT.replace(microsecond=999_999)).epoch == EPOCH


def test_str_uses_discords_default_style() -> None:
    assert str(DiscordTime(MOMENT)) == f"<t:{EPOCH}>"


@pytest.mark.parametrize("style", list(TimestampStyle))
def test_format_spec_is_the_style_letter(style: TimestampStyle) -> None:
    time = DiscordTime(MOMENT)
    assert f"{time:{style}}" == time.format(style) == f"<t:{EPOCH}:{style}>"


def test_unknown_format_spec_is_rejected() -> None:
    with pytest.raises(ValueError, match="'x'"):
        f"{DiscordTime(MOMENT):x}"


def test_with_relative_defaults_to_full_date() -> None:
    assert DiscordTime(MOMENT).with_relative() == f"<t:{EPOCH}:F> (<t:{EPOCH}:R>)"
    assert DiscordTime(MOMENT).with_relative(TimestampStyle.SHORT_DATE) == f"<t:{EPOCH}:d> (<t:{EPOCH}:R>)"
