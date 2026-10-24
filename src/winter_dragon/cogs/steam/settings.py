"""Settings for the Steam sale finder, in its ``cogs.ini`` section."""

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
    default_threshold = CogConfig(100)
    """The discount /steam show lists by default, and a new subscriber's threshold: 100 means free games only."""
    min_sleep = CogConfig(60.0)
    """Seconds the background loop sleeps at least, so a failing re-check is retried at most this often."""
    sale_end_hour = CogConfig(17)
    """The hour (UTC) Steam starts and ends most sales: 10:00 Pacific during daylight saving time."""
    rollover_grace = CogConfig(300)
    """Seconds after Steam's daily rollover the extra scrape runs, giving the store time to update."""
    query_page_size = CogConfig(1000)
    """Items per ``IStoreQueryService/Query`` request; 1000 is the most Steam returns at once."""
    get_items_batch_size = CogConfig(200)
    """Items per ``IStoreBrowseService/GetItems`` request; Steam rejects the URL of a few hundred more."""
    request_timeout = CogConfig(30.0)
    """Seconds a request to Steam may take before it counts as failed."""
    language = CogConfig("english")
    """The language Steam answers in, as a Steam API language name (e.g. ``english``, ``dutch``)."""
    initial_backoff = CogConfig(300.0)
    """Seconds requests pause after a rate-limit answer without a ``Retry-After``; doubles on each further one."""
    max_backoff = CogConfig(3600.0 * 6)
    """The longest pause in seconds, however many rate-limit answers come in a row."""
    items_per_page = CogConfig(5)
    """Sales shown per page of /steam show."""
