"""Tests for wd_discord.timestamp: Discord timestamp markup."""

import math
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from wd_discord.timestamp import DiscordTime, TimestampStyle


MOMENT = datetime(2021, 4, 20, 16, 20, 30, tzinfo=UTC)
EPOCH = 1618935630


@given(
    st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(3000, 1, 1), timezones=st.just(UTC)),  # noqa: DTZ001
    st.sampled_from(TimestampStyle),
)
def test_markup_holds_the_moment_in_whole_seconds(moment: datetime, style: TimestampStyle) -> None:
    time = DiscordTime(moment)
    assert time.epoch == math.floor(moment.timestamp())
    assert f"{time:{style}}" == time.format(style) == f"<t:{time.epoch}:{style}>"
    assert str(time) == f"<t:{time.epoch}>"  # Discord's default style


def test_unknown_format_spec_is_rejected() -> None:
    with pytest.raises(ValueError, match="'x'"):
        f"{DiscordTime(MOMENT):x}"


def test_with_relative_defaults_to_full_date() -> None:
    assert DiscordTime(MOMENT).with_relative() == f"<t:{EPOCH}:F> (<t:{EPOCH}:R>)"
    assert DiscordTime(MOMENT).with_relative(TimestampStyle.SHORT_DATE) == f"<t:{EPOCH}:d> (<t:{EPOCH}:R>)"
