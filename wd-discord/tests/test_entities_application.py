"""Unit tests: CurrentApplication.id's fetch-and-cache behavior."""

import wd_discord.resources.guild.features as _guild_features
import wd_discord.snowflake as _snowflake
from wd_discord.entities import Application
from wd_discord.testing import RecordingClient


# NOTE: on this repo's pinned Python (3.15 beta), pydantic's schema generation for
# ``Application`` fails unless the ``Snowflake`` and ``VerificationLevel`` lazy imports used
# (transitively, via ``Guild``) in its own type annotations have already been resolved once
# elsewhere first - see the "herogold py315 break" memory note for the general issue. Touching
# them here (before constructing any ``Application`` below) is a test-local workaround; it
# doesn't change the behavior under test.
_ = (_snowflake.Snowflake, _guild_features.VerificationLevel)

_APPLICATION_FIELDS = {
    "id": "999",
    "name": "test",
    "icon": None,
    "description": "",
    "bot_public": True,
    "bot_require_code_grant": False,
    "verify_key": "key",
    "team": None,
}


async def test_fetches_and_caches_when_unset() -> None:
    client = RecordingClient(application_id=None)
    client.reply("GET", "/applications/@me", _APPLICATION_FIELDS)

    first = await client.application.id()
    second = await client.application.id()

    assert str(first) == "999"
    assert str(second) == "999"
    assert len(client.requests_to("GET", "/applications/@me")) == 1  # cached after the first call


async def test_given_application_id_is_used_without_fetching() -> None:
    client = RecordingClient(application_id=777)

    assert str(await client.application.id()) == "777"
    assert client.sent == []


async def test_fetch_returns_the_application_entity() -> None:
    client = RecordingClient()
    client.reply("GET", "/applications/@me", _APPLICATION_FIELDS)

    application = await client.application.fetch()

    assert isinstance(application, Application)
    assert application.name == "test"
