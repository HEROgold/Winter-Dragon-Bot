"""Find Steam sales through Steam's store web APIs.

``IStoreQueryService/Query`` lists the items with at least a given discount, best-selling first, 1000 per request;
``IStoreBrowseService/GetItems`` looks up the current discount of many items at once. Both answer without an API key.
Scrapers return plain :class:`ScrapedSale` values and never touch the database; the cog decides what to store.
A request that fails is logged and skipped, so one bad answer never stops a scrape. Every request goes through a
:class:`RequestThrottle`, so a scrape never sends requests fast enough to get rate-limited.
"""

from __future__ import annotations

lazy import json
lazy from dataclasses import dataclass
lazy from enum import Enum, auto
lazy from itertools import batched
lazy from typing import TYPE_CHECKING, Self

lazy from herogold.log import LoggerMixin
lazy from httpxyz import AsyncClient, RequestError
lazy from pydantic import ValidationError

lazy from winter_dragon.cogs.steam.models import SaleTypes
lazy from winter_dragon.cogs.steam.store_api import DLC_APP_TYPE, FOUND, ItemsResponse, QueryResponse
lazy from winter_dragon.cogs.steam.throttle import RequestThrottle
lazy from winter_dragon.cogs.steam.urls import StoreItemKind


if TYPE_CHECKING:
    lazy from collections.abc import AsyncGenerator, Iterable
    lazy from datetime import datetime

    lazy from httpxyz import Response

    lazy from winter_dragon.cogs.steam.store_api import SteamModel, StoreItem
    lazy from winter_dragon.cogs.steam.urls import SteamURL, StoreItemID


STORE_API_URL = "https://api.steampowered.com"
QUERY_URL = f"{STORE_API_URL}/IStoreQueryService/Query/v1/"
GET_ITEMS_URL = f"{STORE_API_URL}/IStoreBrowseService/GetItems/v1/"
QUERY_PAGE_SIZE = 1000
"""Items per ``Query`` request; the most Steam returns at once."""
GET_ITEMS_BATCH_SIZE = 200
"""Items per ``GetItems`` request; Steam rejects the URL of a few hundred more."""
TOP_SELLERS_SORT = 10
"""The ``Query`` sort ordering items by global sales, best-selling first (not in SteamDB's protobufs; found by trying)."""
MIN_DISCOUNT_FILTER = range(1, 100)
"""The ``min_discount_percent`` values Steam honours: it ignores 100 (matching every item), and 0 matches full price."""
REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_REQUEST_INTERVAL = 1.5
"""Seconds between requests for a scraper given no throttle."""
DEFAULT_COUNTRY_CODE = "US"
LANGUAGE = "english"
RATE_LIMITED = 429


class ScrapeFailure(Enum):
    """Why Steam gave no answer, as opposed to answering "not on sale"."""

    UNAVAILABLE = auto()
    """The request failed (network error, non-2xx status, rate limit) or Steam answered something unexpected."""


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

    @classmethod
    def from_store_item(cls, item: StoreItem) -> Self | None:
        """Return the sale on ``item``, or ``None`` when it isn't discounted (or isn't a store item Steam knows)."""
        option = item.best_purchase_option
        url = item.url
        if item.success != FOUND or option is None or option.discount_pct <= 0 or url is None or item.item_id is None:
            return None
        properties: set[SaleTypes] = set()
        if item.item_id.kind is not StoreItemKind.APP:
            properties.add(SaleTypes.BUNDLE)
        elif item.type == DLC_APP_TYPE:
            properties.add(SaleTypes.DLC)
        return cls(
            id=item.id,
            title=item.name or "Bundle",
            url=url,
            sale_percent=option.discount_pct,
            final_price=option.final_price_in_cents / 100,
            properties=frozenset(properties),
            sale_end=option.discount_end,
        )


def _retry_after(response: Response) -> float | None:
    """Return the seconds a response's ``Retry-After`` header asks to wait, if it gives a number."""
    value = response.headers.get("Retry-After", "")
    return float(value) if value.isdigit() else None


class SteamScraper(LoggerMixin):
    """Asks Steam's store APIs for sales; use as ``async with SteamScraper() as scraper``."""

    def __init__(
        self,
        http: AsyncClient | None = None,
        throttle: RequestThrottle | None = None,
        *,
        country_code: str = DEFAULT_COUNTRY_CODE,
    ) -> None:
        """Ask through ``http``, or through a client of its own (closed on exit) when not given.

        Pass the same ``throttle`` to every scraper, so request spacing and rate-limit pauses span all of them.
        Prices are read in the store region ``country_code``.
        """
        self._owns_http = http is None
        self.http = http or AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
        self.throttle = throttle or RequestThrottle(DEFAULT_REQUEST_INTERVAL)
        self.context = {"language": LANGUAGE, "country_code": country_code}

    async def __aenter__(self) -> Self:
        """Enter the context, returning the scraper."""
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close the HTTP client, if this scraper created it."""
        if self._owns_http:
            await self.http.aclose()

    async def _call[T: SteamModel](self, url: str, request: dict[str, object], answer: type[T]) -> T | None:
        """Send ``request`` to the store API at ``url``, or log and return ``None`` when it gives no usable answer."""
        if not await self.throttle.acquire():
            return None
        try:
            response = await self.http.get(url, params={"input_json": json.dumps(request)})
        except RequestError:
            self.logger.exception(t"Request to {url} failed")
            return None
        if response.status_code == RATE_LIMITED:
            pause = self.throttle.rate_limited(_retry_after(response))
            self.logger.warning(t"Steam rate-limited us on {url}; pausing all requests for {pause:.0f}s")
            return None
        self.throttle.succeeded()
        if not response.is_success:
            self.logger.warning(t"Steam answered {response.status_code} for {url}")
            return None
        try:
            return answer.model_validate_json(response.content)
        except ValidationError:
            self.logger.warning(t"Unexpected answer from {url}")
            return None

    def _query(self, percent: int, start: int, count: int) -> dict[str, object]:
        """Build the ``Query`` request for ``count`` best-selling items of at least ``percent`` from ``start`` on."""
        min_discount = min(max(percent, MIN_DISCOUNT_FILTER.start), MIN_DISCOUNT_FILTER.stop - 1)
        return {
            "query_name": "winter-dragon-sales",
            "context": self.context,
            "data_request": {},
            "query": {
                "start": start,
                "count": count,
                "sort": TOP_SELLERS_SORT,
                "filters": {
                    "type_filters": {"include_apps": True, "include_packages": True, "include_bundles": True},
                    "price_filters": {"min_discount_percent": min_discount},
                },
            },
        }

    async def query_sales(self, percent: int, limit: int | None = None) -> AsyncGenerator[ScrapedSale]:
        """Yield the sales of at least ``percent``, best-selling first: the first ``limit``, or every one without.

        Pages through the results :data:`QUERY_PAGE_SIZE` at a time, stopping early at the last result or at a page
        that fails to load.
        """
        start = examined = yielded = 0
        while limit is None or start < limit:
            count = QUERY_PAGE_SIZE if limit is None else min(QUERY_PAGE_SIZE, limit - start)
            page = await self._call(QUERY_URL, self._query(percent, start, count), QueryResponse)
            if page is None:
                break
            items = page.response.store_items
            for item in items:
                examined += 1
                sale = ScrapedSale.from_store_item(item)
                if sale is not None and sale.sale_percent >= percent:
                    yielded += 1
                    yield sale
            start += count
            if not items or start >= page.response.metadata.total_matching_records:
                break
        self.logger.info(t"Steam query: examined={examined} yielded={yielded} threshold={percent} percent, limit={limit}")

    async def get_sales(
        self,
        items: Iterable[StoreItemID],
    ) -> AsyncGenerator[tuple[StoreItemID, ScrapedSale | ScrapeFailure | None]]:
        """Yield each item with its current sale, ``None`` when it isn't on sale, or why Steam gave no answer.

        Looks the items up :data:`GET_ITEMS_BATCH_SIZE` at a time; an item missing from Steam's answer counts as no
        answer, so it's retried later instead of taken for ended.
        """
        for batch in batched(items, GET_ITEMS_BATCH_SIZE, strict=False):
            request: dict[str, object] = {
                "ids": [item.as_request() for item in batch],
                "context": self.context,
                "data_request": {},
            }
            answer = await self._call(GET_ITEMS_URL, request, ItemsResponse)
            found = {} if answer is None else {item.item_id: item for item in answer.response.store_items}
            for item in batch:
                store_item = found.get(item)
                yield item, ScrapeFailure.UNAVAILABLE if store_item is None else ScrapedSale.from_store_item(store_item)
