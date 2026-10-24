"""Shared fixtures for the wd-discord test suite.

Live tests are gated on a real bot token read from the repo ``bot.ini`` (``[Tokens]
discord_token``). When the token is missing or still the ``!!`` placeholder, those tests
are skipped so the unit suite stays green offline and in CI.
"""

lazy import configparser
lazy from pathlib import Path
lazy from typing import TYPE_CHECKING, Any

lazy import pytest
lazy import pytest_asyncio
lazy from httpxyz import Response
lazy from wd_discord import ApiResponseError, Client, DiscordModel
lazy from wd_discord.entities import Entity


if TYPE_CHECKING:
    lazy from collections.abc import AsyncIterator, Callable


def _read_repo_ini(name: str) -> configparser.ConfigParser:
    """Parse the repo ini file ``name``, found by walking up from this file (empty parser if not found)."""
    parser = configparser.ConfigParser(interpolation=None)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / name
        if candidate.is_file():
            parser.read(candidate, encoding="utf-8")
            break
    return parser


@pytest.fixture(scope="session")
def config() -> configparser.ConfigParser:
    """The parsed repo config.ini (empty parser if not found)."""
    return _read_repo_ini("config.ini")


@pytest.fixture(scope="session")
def token() -> str:
    """The bot token from bot.ini, or skip the test if it is unset/placeholder."""
    value = _read_repo_ini("bot.ini").get("Tokens", "discord_token", fallback="").strip()
    if not value or "!!" in value:
        pytest.skip("No usable discord_token in bot.ini; skipping live test.")
    return value


@pytest.fixture(scope="session")
def support_guild_id(config: configparser.ConfigParser) -> str | None:
    """The support guild id from config.ini, if present."""
    value = config.get("Settings", "support_guild_id", fallback="").strip()
    return value or None


@pytest_asyncio.fixture
async def client(token: str) -> AsyncIterator[Client]:
    """A live :class:`Client` for the configured bot token, closed after the test."""
    discord = Client(token)
    try:
        yield discord
    finally:
        await discord.aclose()


@pytest.fixture
def assert_success() -> Callable[[object], Any]:
    """Return a helper that asserts a client call succeeded and returns its result as JSON.

    Accepts a raw :class:`Response`, a data model, or an entity (whose model is used).
    """

    def _assert_success(result: object) -> Any:  # noqa: ANN401 - JSON body may be an object or array
        assert not isinstance(result, ApiResponseError), f"Discord API error: {result!r}"
        if isinstance(result, Entity):
            result = result.model
        if isinstance(result, DiscordModel):
            return result.model_dump(mode="json")
        assert isinstance(result, Response), f"expected a successful Response, got {result!r}"
        assert result.is_success, f"unexpected status {result.status_code}: {result.text}"
        return result.json()

    return _assert_success
