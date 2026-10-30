"""Unit tests: a response body that can't be read as the expected model comes back as an error value (no network)."""

import pytest

from wd_discord.errors import ApiResponseError, JsonErrorCode
from wd_discord.testing import TEST_APPLICATION_ID, RecordingClient


MALFORMED = {"unexpected": "shape"}


def assert_unreadable(result: object) -> None:
    assert isinstance(result, ApiResponseError)
    assert (result.code, result.status) == (JsonErrorCode.GENERAL_ERROR, 200)


async def test_malformed_gateway_bot_is_an_error_value() -> None:
    client = RecordingClient()
    client.reply("GET", "/gateway/bot", MALFORMED)

    assert_unreadable(await client.get_gateway_bot())


async def test_malformed_application_is_an_error_value() -> None:
    client = RecordingClient()
    client.reply("GET", "/applications/@me", MALFORMED)

    assert_unreadable(await client.application.fetch())


@pytest.mark.parametrize("body", [MALFORMED, [MALFORMED]])
async def test_malformed_entitlements_are_an_error_value(body: object) -> None:
    client = RecordingClient()
    client.reply("GET", f"/applications/{TEST_APPLICATION_ID}/entitlements", body)

    assert_unreadable(await client.application.fetch_entitlements())


@pytest.mark.parametrize("body", [MALFORMED, [MALFORMED]])
async def test_malformed_member_search_is_an_error_value(body: object) -> None:
    client = RecordingClient()
    client.reply("GET", "/guilds/1/members/search", body)

    assert_unreadable(await client.guilds.partial(1).search_members("some"))
