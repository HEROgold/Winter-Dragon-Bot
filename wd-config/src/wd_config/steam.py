"""Settings for the Steam sale finder."""

from __future__ import annotations

lazy from confkit.data_types import Hex

lazy from .config import Config


class SteamSettings:
    """How often Steam is scraped, and how its sales are shown."""

    search_url = Config("https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1&supportedlang=english")
    """The Steam search page scraped for sales."""
    update_interval = Config(3600 * 3)
    """Seconds between two scrapes of :attr:`search_url`."""
    outdated_after = Config(3600 * 30)
    """Seconds after its last sighting that a sale counts as outdated, and is hidden or announced again."""
    recheck_delay = Config(60)
    """Seconds after a sale's announced end before its app page is checked again."""
    embed_color = Config(Hex(0x094D7F))
