"""Settings for the Steam sale finder, in its ``cogs.ini`` section."""

from __future__ import annotations

lazy from confkit.data_types import Hex

lazy from winter_dragon.config import CogConfig


class SteamSettings:
    """How often Steam is scraped, and how its sales are shown."""

    country_code = CogConfig("US")
    """The store region prices are read in, as an ISO 3166 country code (e.g. ``NL`` for euro prices)."""
    stored_percent = CogConfig(50)
    """The lowest discount stored, so /steam show can list sales down to it; a lower subscriber threshold goes lower."""
    complete_percent = CogConfig(90)
    """From this discount up every sale is stored; below it, only the :attr:`top_sellers` best-selling ones."""
    top_sellers = CogConfig(2000)
    """Best-selling sales stored per scrape below :attr:`complete_percent`; Steam has ~70k sales of 50% during big sales."""
    request_interval = CogConfig(1.5)
    """Minimum seconds between two requests to Steam, keeping scrapes under Steam's rate limit."""
    update_interval = CogConfig(3600 * 3)
    """Seconds between two scrapes of Steam's sales."""
    outdated_after = CogConfig(3600 * 30)
    """Seconds after its last sighting that a sale counts as outdated, and is hidden or announced again."""
    recheck_delay = CogConfig(60)
    """Seconds after a sale's announced end before it's checked again."""
    embed_color = CogConfig(Hex(0x094D7F))
    """The color of the sale embeds, on /steam show and in the sale DMs."""
    steam_redirect = CogConfig("steam://")
    """An https page redirecting to ``steam://``, for install links; Discord won't render a raw ``steam://`` link."""
