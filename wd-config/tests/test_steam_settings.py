"""Pin the Steam cog's tunables in cogs.ini: today's defaults on a fresh boot, operator values win."""

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from conftest import BootConfig


STEAM_SETTINGS = """
from winter_dragon.cogs.steam.settings import SteamSettings
names = (
    "default_threshold", "min_sleep", "sale_end_hour", "rollover_grace", "query_page_size",
    "get_items_batch_size", "request_timeout", "language", "initial_backoff", "max_backoff", "items_per_page",
)
result = {name: getattr(SteamSettings, name) for name in names}
"""

DEFAULTS = {
    "default_threshold": 100,
    "min_sleep": 60.0,
    "sale_end_hour": 17,
    "rollover_grace": 300,
    "query_page_size": 1000,
    "get_items_batch_size": 200,
    "request_timeout": 30.0,
    "language": "english",
    "initial_backoff": 300.0,
    "max_backoff": 3600.0 * 6,
    "items_per_page": 5,
}


def test_fresh_boot_writes_steam_tunables_with_defaults(boot_config: BootConfig) -> None:
    """With no cogs.ini, the Steam tunables resolve to their defaults and are written to the SteamSettings section."""
    boot = boot_config(STEAM_SETTINGS)

    assert boot.values == DEFAULTS
    assert set(DEFAULTS) <= set(boot.files["cogs.ini"]["SteamSettings"])


def test_prewritten_steam_tunables_resolve(boot_config: BootConfig) -> None:
    """Values already in cogs.ini's SteamSettings section win over the defaults."""
    boot = boot_config(
        STEAM_SETTINGS,
        files={"cogs.ini": "[SteamSettings]\nitems_per_page = 8\nlanguage = dutch\nmax_backoff = 60.0\n"},
    )

    assert boot.values == DEFAULTS | {"items_per_page": 8, "language": "dutch", "max_backoff": 60.0}
