"""Unit tests: Snowflake decoding (API -> object) and pagination round-trip (object -> API)."""

lazy from datetime import UTC, datetime, timedelta

lazy from hypothesis import given
lazy from hypothesis import strategies as st
lazy from wd_discord import Snowflake
lazy from wd_discord.constants import DISCORD_EPOCH
lazy from wd_discord.pagination import snowflake_from_timestamp


# Discord's documented example snowflake.
EXAMPLE_SNOWFLAKE = 175928847299117063
EXAMPLE_TIMESTAMP_MS = 1462015105796


def test_snowflake_components() -> None:
    snowflake = Snowflake(EXAMPLE_SNOWFLAKE)
    assert snowflake.worker_id == 1
    assert snowflake.process_id == 0
    assert snowflake.increment == 7


def test_snowflake_timestamp() -> None:
    snowflake = Snowflake(EXAMPLE_SNOWFLAKE)
    assert snowflake.timestamp == datetime(2016, 4, 30, 11, 18, 25, 796000, tzinfo=UTC)


def test_pagination_builds_time_bits() -> None:
    # snowflake_from_timestamp puts the ms-since-epoch into the high 42 bits.
    assert snowflake_from_timestamp(EXAMPLE_TIMESTAMP_MS) >> 22 == EXAMPLE_TIMESTAMP_MS - 1420070400000


def test_timestamp_round_trip() -> None:
    snowflake = Snowflake(snowflake_from_timestamp(EXAMPLE_TIMESTAMP_MS))
    assert snowflake.timestamp == datetime(2016, 4, 30, 11, 18, 25, 796000, tzinfo=UTC)


@given(st.integers(min_value=0, max_value=2**64 - 1))
def test_a_snowflake_is_its_int_and_prints_as_discords_decimal_string(value: int) -> None:
    snowflake = Snowflake(value)
    assert int(snowflake) == value
    assert str(snowflake) == f"{value}"
    assert Snowflake.coerce(str(snowflake)) == snowflake


@given(
    milliseconds=st.integers(min_value=0, max_value=2**42 - 1),
    worker=st.integers(min_value=0, max_value=31),
    process=st.integers(min_value=0, max_value=31),
    increment=st.integers(min_value=0, max_value=4095),
)
def test_a_snowflake_splits_into_the_parts_it_was_built_from(milliseconds: int, worker: int, process: int, increment: int) -> None:
    """https://docs.discord.com/developers/reference#snowflakes: 42 bits of time, 5 worker, 5 process, 12 increment."""
    snowflake = Snowflake(milliseconds << 22 | worker << 17 | process << 12 | increment)
    assert (snowflake.worker_id, snowflake.process_id, snowflake.increment) == (worker, process, increment)
    assert snowflake.timestamp == datetime.fromtimestamp(DISCORD_EPOCH / 1000, tz=UTC) + timedelta(milliseconds=milliseconds)


@given(st.integers(min_value=DISCORD_EPOCH, max_value=DISCORD_EPOCH + 2**42 - 1))
def test_a_pagination_snowflake_carries_its_timestamp(unix_milliseconds: int) -> None:
    snowflake = Snowflake(snowflake_from_timestamp(unix_milliseconds))
    assert snowflake.timestamp == datetime.fromtimestamp(0, tz=UTC) + timedelta(milliseconds=unix_milliseconds)
