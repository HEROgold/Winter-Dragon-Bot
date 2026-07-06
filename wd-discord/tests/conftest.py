"""Shared fixtures for the wd-discord test suite.

Live tests are gated on a real bot token read from the repo ``config.ini`` (``[Tokens]
discord_token``). When the token is missing or still the ``!!`` placeholder, those tests
are skipped so the unit suite stays green offline and in CI.
"""
from __future__ import annotations

import configparser
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
from httpxyz import Response
from wd_discord import ApiResponseError, Client


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


def _find_config_ini() -> Path | None:
    """Walk up from this file to locate the repo ``config.ini``."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config.ini"
        if candidate.is_file():
            return candidate
    return None


@pytest.fixture(scope="session")
def config() -> configparser.ConfigParser:
    """The parsed repo config.ini (empty parser if not found)."""
    parser = configparser.ConfigParser(interpolation=None)
    path = _find_config_ini()
    if path is not None:
        parser.read(path, encoding="utf-8")
    return parser


@pytest.fixture(scope="session")
def token(config: configparser.ConfigParser) -> str:
    """The bot token, or skip the test if it is unset/placeholder."""
    value = config.get("Tokens", "discord_token", fallback="").strip()
    if not value or "!!" in value:
        pytest.skip("No usable discord_token in config.ini; skipping live test.")
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
    """Return a helper that asserts a client call succeeded and returns its JSON body."""

    def _assert_success(result: object) -> Any:  # noqa: ANN401 - JSON body may be an object or array
        assert not isinstance(result, ApiResponseError), f"Discord API error: {result!r}"
        assert isinstance(result, Response), f"expected a successful Response, got {result!r}"
        assert result.is_success, f"unexpected status {result.status_code}: {result.text}"
        return result.json()

    return _assert_success
