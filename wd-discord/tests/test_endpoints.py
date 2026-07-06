"""Unit tests: the API base URL and version are pinned to Discord v10."""
from __future__ import annotations

from wd_config.discord import URLS
from wd_discord import Client


def test_version_is_10() -> None:
    assert URLS().version == 10


def test_api_version_string() -> None:
    assert URLS().api_version == "v10"


def test_base_url() -> None:
    assert URLS().base == "https://discord.com/api"


def test_full_v10_base() -> None:
    urls = URLS()
    assert f"{urls.base}/{urls.api_version}" == "https://discord.com/api/v10"


def test_client_pins_v10() -> None:
    assert Client("token").base_url == "https://discord.com/api/v10"


def test_client_version_override() -> None:
    assert Client("token", version=9).base_url == "https://discord.com/api/v9"
