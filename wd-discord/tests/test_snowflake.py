"""Unit tests: Snowflake decoding (API -> object) and pagination round-trip (object -> API)."""
from __future__ import annotations

lazy from datetime import UTC, datetime

lazy from wd_discord import Snowflake
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
