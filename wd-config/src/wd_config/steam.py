"""Settings for the Steam sale finder."""

from __future__ import annotations

lazy from confkit.data_types import Hex

lazy from .config import Config


class SteamSettings:
    """How often Steam is scraped, and how its sales are shown."""

    country_code = Config("US")
    """The store region prices are read in, as an ISO 3166 country code (e.g. ``NL`` for euro prices)."""
    stored_percent = Config(50)
    """The lowest discount stored, so /steam show can list sales down to it; a lower subscriber threshold goes lower."""
    complete_percent = Config(90)
    """From this discount up every sale is stored; below it, only the :attr:`top_sellers` best-selling ones."""
    top_sellers = Config(2000)
    """Best-selling sales stored per scrape below :attr:`complete_percent`; Steam has ~70k sales of 50% during big sales."""
    request_interval = Config(1.5)
    """Minimum seconds between two requests to Steam, keeping scrapes under Steam's rate limit."""
    update_interval = Config(3600 * 3)
    """Seconds between two scrapes of Steam's sales."""
    outdated_after = Config(3600 * 30)
    """Seconds after its last sighting that a sale counts as outdated, and is hidden or announced again."""
    recheck_delay = Config(60)
    """Seconds after a sale's announced end before it's checked again."""
    embed_color = Config(Hex(0x094D7F))
