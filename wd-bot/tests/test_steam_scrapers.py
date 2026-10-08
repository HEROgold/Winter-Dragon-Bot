"""Unit tests: Steam URLs, store item parsing, and the scrapers against canned store API answers (no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict

import httpxyz
import pytest
from pydantic import TypeAdapter

from winter_dragon.cogs.steam.models import SaleTypes
from winter_dragon.cogs.steam.scrapers import (
    GET_ITEMS_BATCH_SIZE,
    QUERY_PAGE_SIZE,
    ScrapedSale,
    ScrapeFailure,
    SteamScraper,
)
from winter_dragon.cogs.steam.store_api import StoreItem
from winter_dragon.cogs.steam.throttle import RequestThrottle
from winter_dragon.cogs.steam.urls import SteamURL, StoreItemID, StoreItemKind


if TYPE_CHECKING:
    from collections.abc import Callable


END = 1791478800  # 2026-10-08 17:00 UTC
GIVEAWAY_END = 1792083600  # 2026-10-15 17:00 UTC


def _item(
    item_id: int,
    *,
    percent: int = 90,
    cents: int = 399,
    item_type: int = 0,
    app_type: int = 0,
    path: str | None = None,
) -> dict[str, object]:
    """Build a store item the way Steam's APIs answer it."""
    option: dict[str, object] = {"final_price_in_cents": str(cents), "original_price_in_cents": "3999"}
    if percent:
        option |= {"discount_pct": percent, "active_discounts": [{"discount_end_date": END}]}
    kind = ("app", "sub", "bundle")[item_type]
    return {
        "item_type": item_type,
        "id": item_id,
        "success": 1,
        "name": f"Item {item_id}",
        "store_url_path": f"{kind}/{item_id}/Item" if path is None else path,
        "type": app_type,
        "best_purchase_option": option,
    }


GIVEAWAY: dict[str, object] = {
    "item_type": 0,
    "id": 5067220,
    "success": 1,
    "name": "Rotwood: Drakin Armoury Pack",
    "store_url_path": "app/5067220/Rotwood_Drakin_Armoury_Pack",
    "type": 4,
    "best_purchase_option": {
        "final_price_in_cents": "0",
        "original_price_in_cents": "499",
        "discount_pct": 100,
        "is_free_to_keep": True,
        "free_to_keep_ends": GIVEAWAY_END,
    },
}


def _scraper(respond: Callable[[httpxyz.Request], httpxyz.Response]) -> SteamScraper:
    return SteamScraper(httpxyz.AsyncClient(transport=httpxyz.MockTransport(respond)), RequestThrottle(0))


class QueryParams(TypedDict):
    start: int
    count: int
    sort: int
    filters: dict[str, dict[str, object]]


class QueryRequest(TypedDict):
    """The ``input_json`` of a ``Query`` request."""

    query: QueryParams
    context: dict[str, str]


class ItemsRequest(TypedDict):
    """The ``input_json`` of a ``GetItems`` request."""

    ids: list[dict[str, int]]


def _query_input(request: httpxyz.Request) -> QueryRequest:
    return TypeAdapter(QueryRequest).validate_json(request.url.params["input_json"])


def _items_input(request: httpxyz.Request) -> ItemsRequest:
    return TypeAdapter(ItemsRequest).validate_json(request.url.params["input_json"])


def _query_server(
    items: list[dict[str, object]], requests: list[QueryRequest]
) -> Callable[[httpxyz.Request], httpxyz.Response]:
    """Answer ``Query`` requests like Steam: the page of ``items`` asked for, and their total count."""

    def respond(request: httpxyz.Request) -> httpxyz.Response:
        body = _query_input(request)
        requests.append(body)
        start, count = body["query"]["start"], body["query"]["count"]
        page = items[start : start + count]
        metadata = {"total_matching_records": len(items), "start": start, "count": len(page)}
        return httpxyz.Response(200, json={"response": {"metadata": metadata, "store_items": page}})

    return respond


@pytest.mark.parametrize(
    ("url", "app_id", "is_bundle", "item"),
    [
        ("https://store.steampowered.com/app/1168660/Barro_2020/", 1168660, False, StoreItemID(StoreItemKind.APP, 1168660)),
        ("https://store.steampowered.com/bundle/555/Big_Pack/", None, True, StoreItemID(StoreItemKind.BUNDLE, 555)),
        ("https://store.steampowered.com/sub/66335/", None, True, StoreItemID(StoreItemKind.PACKAGE, 66335)),
        ("https://store.steampowered.com/search/", None, False, None),
    ],
)
def test_steam_url(url: str, app_id: int | None, *, is_bundle: bool, item: StoreItemID | None) -> None:
    steam_url = SteamURL(url)
    assert steam_url.app_id == app_id
    assert steam_url.is_app is (app_id is not None)
    assert steam_url.is_bundle is is_bundle
    assert steam_url.store_item == item


def test_store_item_id_round_trips_through_its_url() -> None:
    item = StoreItemID(StoreItemKind.PACKAGE, 42)
    assert item.url.store_item == item
    assert item.as_request() == {"packageid": 42}


def test_sale_from_a_discounted_app() -> None:
    sale = ScrapedSale.from_store_item(StoreItem.model_validate(_item(1304930)))
    assert sale == ScrapedSale(
        id=1304930,
        title="Item 1304930",
        url=SteamURL("https://store.steampowered.com/app/1304930/Item"),
        sale_percent=90,
        final_price=3.99,
        sale_end=datetime.fromtimestamp(END, UTC),
    )


def test_free_giveaway_is_a_dlc_ending_when_it_can_no_longer_be_claimed() -> None:
    sale = ScrapedSale.from_store_item(StoreItem.model_validate(GIVEAWAY))
    assert sale is not None
    assert (sale.sale_percent, sale.final_price) == (100, 0.0)
    assert sale.properties == frozenset({SaleTypes.DLC})
    assert sale.sale_end == datetime.fromtimestamp(GIVEAWAY_END, UTC)


def test_packages_are_bundles_keyed_by_their_own_id() -> None:
    sale = ScrapedSale.from_store_item(StoreItem.model_validate(_item(648168, item_type=1, path="sub/648168/")))
    assert sale is not None
    assert sale.properties == frozenset({SaleTypes.BUNDLE})
    assert sale.url.store_item == StoreItemID(StoreItemKind.PACKAGE, 648168)


@pytest.mark.parametrize(
    "item",
    [
        _item(10, percent=0),  # full price
        {"item_type": 0, "id": 999999999, "success": 15, "name": "", "store_url_path": "app/0/", "appid": 0},  # unknown
        {"item_type": 0, "id": 730, "success": 1, "name": "Counter-Strike 2", "is_free": True},  # free to play
    ],
)
def test_items_without_a_discount_are_no_sale(item: dict[str, object]) -> None:
    assert ScrapedSale.from_store_item(StoreItem.model_validate(item)) is None


async def test_query_asks_for_top_sellers_with_the_discount_and_filters_the_rest() -> None:
    requests: list[QueryRequest] = []
    items = [_item(1, percent=95), _item(2, percent=60), _item(3, percent=90, item_type=2)]
    async with _scraper(_query_server(items, requests)) as scraper:
        sales = [sale async for sale in scraper.query_sales(90)]

    assert [sale.id for sale in sales] == [1, 3]
    (body,) = requests
    query = body["query"]
    assert query["sort"] == 10
    assert query["filters"]["price_filters"] == {"min_discount_percent": 90}
    assert body["context"] == {"language": "english", "country_code": "US"}


@pytest.mark.parametrize(("percent", "sent"), [(100, 99), (0, 1)])
async def test_query_sends_a_discount_filter_steam_honours(percent: int, sent: int) -> None:
    requests: list[QueryRequest] = []
    async with _scraper(_query_server([GIVEAWAY, _item(1, percent=99)], requests)) as scraper:
        sales = [sale async for sale in scraper.query_sales(percent)]

    query = requests[0]["query"]
    assert query["filters"]["price_filters"] == {"min_discount_percent": sent}
    assert len(sales) == (1 if percent == 100 else 2)  # the 99% sale isn't free


async def test_query_pages_through_every_result_without_a_limit() -> None:
    requests: list[QueryRequest] = []
    items = [_item(index) for index in range(QUERY_PAGE_SIZE + 5)]
    async with _scraper(_query_server(items, requests)) as scraper:
        sales = [sale async for sale in scraper.query_sales(50)]
    assert len(sales) == QUERY_PAGE_SIZE + 5
    assert len(requests) == 2


async def test_query_stops_at_the_limit() -> None:
    requests: list[QueryRequest] = []
    items = [_item(index) for index in range(QUERY_PAGE_SIZE + 5)]
    async with _scraper(_query_server(items, requests)) as scraper:
        sales = [sale async for sale in scraper.query_sales(50, limit=3)]
    assert [sale.id for sale in sales] == [0, 1, 2]
    query = requests[0]["query"]
    assert query["count"] == 3


async def test_query_keeps_the_pages_before_a_failing_one() -> None:
    items = [_item(index) for index in range(QUERY_PAGE_SIZE + 5)]
    serve = _query_server(items, [])

    def respond(request: httpxyz.Request) -> httpxyz.Response:
        return serve(request) if _query_input(request)["query"]["start"] == 0 else httpxyz.Response(503)

    async with _scraper(respond) as scraper:
        sales = [sale async for sale in scraper.query_sales(50)]
    assert len(sales) == QUERY_PAGE_SIZE


async def test_unexpected_answer_is_no_answer() -> None:
    async with _scraper(lambda _request: httpxyz.Response(200, json={"oops": True})) as scraper:
        assert [sale async for sale in scraper.query_sales(50)] == []


async def test_get_sales_tells_running_ended_and_unanswered_items_apart() -> None:
    running, ended, missing = (StoreItemID(StoreItemKind.APP, app_id) for app_id in (1, 2, 3))
    answer = {"response": {"store_items": [_item(1), _item(2, percent=0)]}}
    async with _scraper(lambda _request: httpxyz.Response(200, json=answer)) as scraper:
        results = {item: sale async for item, sale in scraper.get_sales([running, ended, missing])}

    assert isinstance(results[running], ScrapedSale)
    assert results[ended] is None
    assert results[missing] is ScrapeFailure.UNAVAILABLE


async def test_get_sales_asks_in_batches() -> None:
    asked: list[int] = []

    def respond(request: httpxyz.Request) -> httpxyz.Response:
        ids = _items_input(request)["ids"]
        asked.append(len(ids))
        return httpxyz.Response(200, json={"response": {"store_items": [_item(entry["appid"]) for entry in ids]}})

    items = [StoreItemID(StoreItemKind.APP, app_id) for app_id in range(GET_ITEMS_BATCH_SIZE + 1)]
    async with _scraper(respond) as scraper:
        results = [sale async for _item_id, sale in scraper.get_sales(items)]

    assert asked == [GET_ITEMS_BATCH_SIZE, 1]
    assert all(isinstance(sale, ScrapedSale) for sale in results)


async def test_rate_limit_pauses_every_following_request() -> None:
    requests: list[str] = []

    def respond(request: httpxyz.Request) -> httpxyz.Response:
        requests.append(request.url.path)
        return httpxyz.Response(429, headers={"Retry-After": "120"})

    throttle = RequestThrottle(0)
    items = [StoreItemID(StoreItemKind.APP, 1)]
    async with SteamScraper(httpxyz.AsyncClient(transport=httpxyz.MockTransport(respond)), throttle) as scraper:
        first = [sale async for _item_id, sale in scraper.get_sales(items)]
        second = [sale async for _item_id, sale in scraper.get_sales(items)]

    assert first == second == [ScrapeFailure.UNAVAILABLE]
    assert len(requests) == 1  # the second request was never sent
    assert throttle.paused
