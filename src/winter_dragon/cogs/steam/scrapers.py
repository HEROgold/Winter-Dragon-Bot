"""Scrape Steam's store pages for sales.

Scrapers return plain :class:`ScrapedSale` values and never touch the database; the cog decides what to store.
A page that fails to load or parse is logged and skipped, so one bad page never stops a scrape.
"""

from __future__ import annotations

lazy import re
lazy from collections import Counter
lazy from dataclasses import dataclass, field
lazy from datetime import UTC, datetime, timedelta
lazy from enum import Enum, auto
lazy from typing import TYPE_CHECKING, Self

lazy from bs4 import BeautifulSoup, Tag
lazy from herogold.log import LoggerMixin
lazy from httpxyz import AsyncClient, RequestError

lazy from winter_dragon.cogs.steam.models import SaleTypes
lazy from winter_dragon.cogs.steam.tags import (
    ADD_TO_CART,
    DATA_APPID,
    DISCOUNT_FINAL_PRICE,
    DISCOUNT_PERCENT,
    DISCOUNT_PRICES,
    DLC_BANNER,
    GAME_BUY_AREA,
    SALE_END_DATE,
    SALE_END_HOUR_UTC,
    SALE_END_TIMESTAMP,
    SEARCH_GAME_TITLE,
    SINGLE_GAME_TITLE,
    price_to_num,
)
lazy from winter_dragon.cogs.steam.urls import SteamURL


if TYPE_CHECKING:
    lazy from collections.abc import AsyncGenerator


STORE_COOKIES = {
    "birthtime": "0",
    "lastagecheckage": "1-0-1990",
    "mature_content": "1",
    "wants_mature_content": "1",
    "Steam_Language": "english",
}
"""Pass Steam's age gate and get English pages, so the "Offer ends" text can be parsed."""
REQUEST_TIMEOUT_SECONDS = 30.0
BUNDLE_ID_PATTERN = re.compile(r"/(?:sub|bundle)/(\d+)")
DATE_ONLY_ROLLOVER = timedelta(days=180)
"""A date-only sale end this far in the past belongs to next year (e.g. "Offer ends 3 January" seen in December)."""


class ScrapeFailure(Enum):
    """Why a page gave no answer, as opposed to answering "not on sale"."""

    PAGE_UNAVAILABLE = auto()
    """The page failed to load (network error or non-2xx status)."""


@dataclass(frozen=True)
class ScrapedSale:
    """One sale as found on Steam."""

    id: int
    """The Steam app ID, or the bundle/sub ID for bundles."""
    title: str
    url: SteamURL
    sale_percent: int
    final_price: float
    properties: frozenset[SaleTypes] = frozenset()
    sale_end: datetime | None = None


def parse_sale_end(buy_area_html: str, now: datetime) -> datetime | None:
    """Return when the sale in a buy area ends, or ``None`` when Steam doesn't say.

    Prefers the countdown's exact timestamp. A date-only "Offer ends 15 October" is taken to end at
    :data:`SALE_END_HOUR_UTC` that day, in the year that puts it closest to ``now``.
    """
    if timestamp := SALE_END_TIMESTAMP.search(buy_area_html):
        return datetime.fromtimestamp(int(timestamp[1]), UTC)
    if not (date := SALE_END_DATE.search(buy_area_html)):
        return None
    day = datetime.strptime(f"{date[1]} {now.year}", "%d %B %Y").replace(hour=SALE_END_HOUR_UTC, tzinfo=UTC)
    return day.replace(year=now.year + 1) if day < now - DATE_ONLY_ROLLOVER else day


@dataclass
class SearchDiagnostics:
    """Why sales on a search page were skipped, logged once per scrape."""

    percent_threshold: int
    examined: int = 0
    yielded: int = 0
    skipped: Counter[str] = field(default_factory=Counter[str])

    def skip(self, reason: str) -> None:
        """Count one sale skipped for ``reason``."""
        self.skipped[reason] += 1

    def summary(self) -> str:
        """Describe the scrape in one line."""
        reasons = ", ".join(f"{reason}={count}" for reason, count in self.skipped.items()) or "none"
        return (
            f"Steam search: examined={self.examined} yielded={self.yielded} "
            f"threshold={self.percent_threshold}% skipped: {reasons}"
        )


class SteamScraper(LoggerMixin):
    """Fetches Steam store pages and extracts sales from them; use as ``async with SteamScraper() as scraper``."""

    def __init__(self, http: AsyncClient | None = None) -> None:
        """Scrape through ``http``, or through a client of its own (closed on exit) when not given."""
        self._owns_http = http is None
        self.http = http or AsyncClient(cookies=STORE_COOKIES, follow_redirects=True, timeout=REQUEST_TIMEOUT_SECONDS)

    async def __aenter__(self) -> Self:
        """Enter the context, returning the scraper."""
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close the HTTP client, if this scraper created it."""
        if self._owns_http:
            await self.http.aclose()

    async def _get_soup(self, url: str) -> BeautifulSoup | None:
        """Fetch and parse ``url``, or log and return ``None`` when it can't be loaded."""
        try:
            response = await self.http.get(url, headers={"Accept-Language": "en-US,en;q=0.9"})
        except RequestError:
            self.logger.exception(t"Request to {url} failed")
            return None
        if not response.is_success:
            self.logger.warning(t"Steam answered {response.status_code} for {url}")
            return None
        return BeautifulSoup(response.text, "html.parser")

    async def get_game_sale(self, url: SteamURL, now: datetime | None = None) -> ScrapedSale | ScrapeFailure | None:
        """Return the sale on an app page, ``None`` when the app isn't discounted, or why the page gave no answer."""
        app_id = url.app_id
        if app_id is None:
            self.logger.warning(t"Not an app page: {url}")
            return None
        soup = await self._get_soup(url)
        if soup is None:
            return ScrapeFailure.PAGE_UNAVAILABLE
        add_to_cart = soup.find(class_=ADD_TO_CART)
        buy_area = add_to_cart.find_parent(class_=GAME_BUY_AREA) if add_to_cart else None
        if not isinstance(buy_area, Tag):
            self.logger.debug(t"No buy area on {url}")
            return None
        sale_percent = buy_area.find(class_=DISCOUNT_PERCENT)
        price = buy_area.find(class_=DISCOUNT_FINAL_PRICE)
        title = soup.find(class_=SINGLE_GAME_TITLE)
        if not isinstance(sale_percent, Tag) or not isinstance(price, Tag) or not isinstance(title, Tag):
            self.logger.debug(t"{url} is not on sale")
            return None
        properties = frozenset({SaleTypes.DLC}) if soup.find(class_=DLC_BANNER) else frozenset[SaleTypes]()
        return ScrapedSale(
            id=app_id,
            title=title.get_text(strip=True),
            url=url,
            sale_percent=abs(int(sale_percent.get_text(strip=True).strip("-%"))),
            final_price=price_to_num(price.get_text(strip=True)),
            properties=properties,
            sale_end=parse_sale_end(str(buy_area), now or datetime.now(UTC)),
        )

    async def get_sales_from_search(self, search_url: str, percent: int) -> AsyncGenerator[ScrapedSale]:
        """Yield every sale of at least ``percent`` on a Steam search page."""
        soup = await self._get_soup(search_url)
        if soup is None:
            return
        diagnostics = SearchDiagnostics(percent_threshold=percent)
        for prices in soup.find_all(class_=DISCOUNT_PRICES):
            diagnostics.examined += 1
            if (sale := await self._sale_from_search_result(prices, percent, diagnostics)) is not None:
                diagnostics.yielded += 1
                yield sale
        self.logger.info(t"{diagnostics.summary()}")

    async def _sale_from_search_result(
        self,
        prices: Tag,
        percent: int,
        diagnostics: SearchDiagnostics,
    ) -> ScrapedSale | None:
        """Extract the sale from one search result's price block, or record why it was skipped."""
        anchor = prices.find_parent("a", href=True)
        if not isinstance(anchor, Tag):
            diagnostics.skip("missing_anchor")
            return None
        url = SteamURL(str(anchor["href"]).split("?", maxsplit=1)[0])  # drop Steam's ?snr= tracking parameters
        price = anchor.find(class_=DISCOUNT_FINAL_PRICE)
        title = anchor.find(class_=SEARCH_GAME_TITLE)
        if not isinstance(price, Tag) or not isinstance(title, Tag):
            diagnostics.skip("missing_price_or_title")
            return None
        discount = prices.parent.find(class_=DISCOUNT_PERCENT) if prices.parent else None
        if not isinstance(discount, Tag):
            return await self._sale_from_app_page(url, diagnostics)
        sale_percent = abs(int(discount.get_text(strip=True).strip("-%")))
        if sale_percent < percent:
            diagnostics.skip("below_threshold")
            return None
        sale_id = self._sale_id(url, anchor)
        if sale_id is None:
            diagnostics.skip("missing_id")
            return None
        return ScrapedSale(
            id=sale_id,
            title=title.get_text(strip=True) or "Bundle",
            url=url,
            sale_percent=sale_percent,
            final_price=price_to_num(price.get_text(strip=True)),
            properties=frozenset({SaleTypes.BUNDLE}) if url.is_bundle else frozenset[SaleTypes](),
        )

    async def _sale_from_app_page(self, url: SteamURL, diagnostics: SearchDiagnostics) -> ScrapedSale | None:
        """Look up a sale whose search result hides the discount on its app page, which shows it."""
        sale = await self.get_game_sale(url) if url.is_app else None
        if not isinstance(sale, ScrapedSale):
            diagnostics.skip("app_page_lookup_failed")
            return None
        return sale

    @staticmethod
    def _sale_id(url: SteamURL, anchor: Tag) -> int | None:
        """Return a result's app ID, or for bundles the bundle/sub ID from the URL (their app ID lists every item)."""
        if url.is_bundle:
            match = BUNDLE_ID_PATTERN.search(url)
            return int(match[1]) if match else None
        app_id = str(anchor.get(DATA_APPID) or "").split(",", maxsplit=1)[0]
        return int(app_id) if app_id.isdigit() else url.app_id
