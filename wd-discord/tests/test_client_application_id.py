"""Unit tests: Client._get_application_id's fetch-and-cache behavior."""
from __future__ import annotations

# NOTE: on this repo's pinned Python (3.15 beta), pydantic's schema generation for
# ``Application`` fails unless the ``Snowflake`` and ``VerificationLevel`` lazy imports used
# (transitively, via ``Guild``) in its own type annotations have already been resolved once
# elsewhere first - see the "herogold py315 break" memory note for the general issue. Touching
# them here (before anything imports ``Application``) is a test-local workaround; it doesn't
# change the behavior under test.
import wd_discord.resources.guild.features as _features
import wd_discord.snowflake as _snowflake

_ = (_snowflake.Snowflake, _features.VerificationLevel)

import pytest
from wd_config.bot import Settings
from wd_discord import Client
from wd_discord.resources.application import Application

_APPLICATION_FIELDS = {
    "id": "999",
    "name": "test",
    "icon": None,
    "description": "",
    # Required fields on the current ``Application`` model with no defaults; the task brief's
    # sample payload predates them, so they're filled in with innocuous placeholder values.
    "bot_public": True,
    "bot_require_code_grant": False,
    "verify_key": "key",
    "team": None,
}


@pytest.fixture(autouse=True)
def _reset_application_id() -> None:
    original = Settings.application_id
    yield
    Settings.application_id = original


async def test_fetches_and_caches_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    Settings.application_id = None
    client = Client("token")
    calls = 0

    async def fake_get_current_application() -> Application:
        nonlocal calls
        calls += 1
        return Application.model_validate(_APPLICATION_FIELDS)

    monkeypatch.setattr(client, "get_current_application", fake_get_current_application)

    first = await client._get_application_id()  # noqa: SLF001 - testing the private cache path directly
    second = await client._get_application_id()  # noqa: SLF001

    assert first == "999"
    assert second == "999"
    assert calls == 1  # cached after the first call
    assert Settings.application_id == 999  # written back


async def test_uses_configured_value_without_fetching(monkeypatch: pytest.MonkeyPatch) -> None:
    Settings.application_id = 555
    client = Client("token")

    async def fail_if_called() -> Application:
        pytest.fail("should not fetch when Settings.application_id is already set")

    monkeypatch.setattr(client, "get_current_application", fail_if_called)

    assert await client._get_application_id() == "555"
