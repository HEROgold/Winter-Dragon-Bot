"""Unit tests: Steam URL, price and sale-end parsing, and the scrapers against canned store pages (no network)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpxyz
import pytest

from winter_dragon.cogs.steam.models import SaleTypes
from winter_dragon.cogs.steam.scrapers import ScrapedSale, ScrapeFailure, SteamScraper, parse_sale_end
from winter_dragon.cogs.steam.tags import price_to_num
from winter_dragon.cogs.steam.urls import SteamURL


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
TIMER_END = 1791478800  # 2026-10-08 17:00 UTC

APP_ON_SALE = f"""
<div class="apphub_AppName">Barro 2020</div>
<div class="game_area_purchase_game_wrapper"><div class="game_area_purchase_game">
  <div class="game_purchase_discount_countdown">SPECIAL PROMOTION! Offer ends in</div>
  <div class="discount_pct">-90%</div><div class="discount_final_price">0,49€</div>
  <div class="btn_addtocart"><a href="#">Add to Cart</a></div>
  <script>$DiscountCountdown = $J( '#1_countdown_0' ); if ( $DiscountCountdown )
    InitDailyDealTimer( $DiscountCountdown, {TIMER_END} );</script>
</div></div>
"""
DLC_ON_SALE_UNTIL_DATE = """
<div class="apphub_AppName">Signature Pack</div>
<div class="game_area_dlc_bubble">This content requires the base game</div>
<div class="game_area_purchase_game_wrapper"><div class="game_area_purchase_game">
  <p class="game_purchase_discount_countdown">SPECIAL PROMOTION! Offer ends 15 October</p>
  <div class="discount_pct">-100%</div><div class="discount_final_price">0,--€</div>
  <div class="btn_addtocart"><a href="#">Add to Cart</a></div>
</div></div>
"""
APP_NOT_ON_SALE = """
<div class="apphub_AppName">Full Price</div>
<div class="game_area_purchase_game_wrapper"><div class="game_area_purchase_game">
  <div class="game_purchase_price price">19,99€</div>
  <div class="btn_addtocart"><a href="#">Add to Cart</a></div>
</div></div>
"""
SEARCH_PAGE = """
<a href="https://store.steampowered.com/app/10/Free_Game/?snr=1_7_7" data-ds-appid="10">
  <span class="title">Free Game</span>
  <div class="discount_block"><div class="discount_pct">-100%</div>
    <div class="discount_prices"><div class="discount_final_price">Free</div></div></div>
</a>
<a href="https://store.steampowered.com/bundle/555/Big_Pack/?snr=1" data-ds-appid="1,2,3">
  <span class="title">Big Pack</span>
  <div class="discount_block"><div class="discount_pct">-100%</div>
    <div class="discount_prices"><div class="discount_final_price">0,00€</div></div></div>
</a>
<a href="https://store.steampowered.com/app/11/Cheap/" data-ds-appid="11">
  <span class="title">Cheap</span>
  <div class="discount_block"><div class="discount_pct">-20%</div>
    <div class="discount_prices"><div class="discount_final_price">7,99€</div></div></div>
</a>
<a href="https://store.steampowered.com/app/1168660/Barro_2020/" data-ds-appid="1168660">
  <span class="title">Barro 2020</span>
  <div class="discount_block"><div class="discount_prices"><div class="discount_final_price">0,49€</div></div></div>
</a>
"""
PAGES = {
    "/search/": SEARCH_PAGE,
    "/app/1168660/Barro_2020/": APP_ON_SALE,
    "/app/1168660/": APP_ON_SALE,
    "/app/4114140/": DLC_ON_SALE_UNTIL_DATE,
    "/app/30/": APP_NOT_ON_SALE,
}


def _scraper() -> SteamScraper:
    """Build a scraper whose HTTP client serves :data:`PAGES`, and 503 for anything else."""

    def respond(request: httpxyz.Request) -> httpxyz.Response:
        page = PAGES.get(request.url.path)
        return httpxyz.Response(200, text=page) if page is not None else httpxyz.Response(503)

    return SteamScraper(httpxyz.AsyncClient(transport=httpxyz.MockTransport(respond)))


@pytest.mark.parametrize(
    ("url", "app_id", "is_bundle"),
    [
        ("https://store.steampowered.com/app/1168660/Barro_2020/", 1168660, False),
        ("https://store.steampowered.com/bundle/555/Big_Pack/", None, True),
        ("https://store.steampowered.com/sub/66335/", None, True),
    ],
)
def test_steam_url(url: str, app_id: int | None, *, is_bundle: bool) -> None:
    steam_url = SteamURL(url)
    assert steam_url.app_id == app_id
    assert steam_url.is_app is (app_id is not None)
    assert steam_url.is_bundle is is_bundle


@pytest.mark.parametrize(
    ("displayed", "number"),
    [("0,49€", 0.49), ("$0.99 USD", 0.99), ("0,--€", 0.0), ("Free", 0.0), ("19,99€", 19.99)],
)
def test_price_to_num(displayed: str, number: float) -> None:
    assert price_to_num(displayed) == number


def test_sale_end_prefers_the_countdown_timestamp() -> None:
    assert parse_sale_end(APP_ON_SALE, NOW) == datetime.fromtimestamp(TIMER_END, UTC)


def test_date_only_sale_end_is_17_utc_that_day() -> None:
    assert parse_sale_end(DLC_ON_SALE_UNTIL_DATE, NOW) == datetime(2026, 10, 15, 17, tzinfo=UTC)


def test_date_only_sale_end_rolls_over_into_next_year() -> None:
    december = datetime(2026, 12, 20, tzinfo=UTC)
    assert parse_sale_end("Offer ends 3 January", december) == datetime(2027, 1, 3, 17, tzinfo=UTC)


def test_sale_end_already_passed_today_stays_today() -> None:
    evening = datetime(2026, 10, 8, 20, tzinfo=UTC)
    assert parse_sale_end("Offer ends 8 October", evening) == datetime(2026, 10, 8, 17, tzinfo=UTC)


def test_no_sale_end_without_countdown_or_date() -> None:
    assert parse_sale_end(APP_NOT_ON_SALE, NOW) is None


async def test_game_sale_from_app_page() -> None:
    async with _scraper() as scraper:
        sale = await scraper.get_game_sale(SteamURL("https://store.steampowered.com/app/1168660/"), NOW)
    assert sale == ScrapedSale(
        id=1168660,
        title="Barro 2020",
        url=SteamURL("https://store.steampowered.com/app/1168660/"),
        sale_percent=90,
        final_price=0.49,
        sale_end=datetime.fromtimestamp(TIMER_END, UTC),
    )


async def test_dlc_is_detected_on_its_app_page() -> None:
    async with _scraper() as scraper:
        sale = await scraper.get_game_sale(SteamURL("https://store.steampowered.com/app/4114140/"), NOW)
    assert isinstance(sale, ScrapedSale)
    assert sale.properties == frozenset({SaleTypes.DLC})
    assert sale.sale_end == datetime(2026, 10, 15, 17, tzinfo=UTC)


async def test_app_without_discount_is_not_a_sale() -> None:
    async with _scraper() as scraper:
        assert await scraper.get_game_sale(SteamURL("https://store.steampowered.com/app/30/"), NOW) is None


async def test_unavailable_page_is_a_failure_not_a_missing_sale() -> None:
    async with _scraper() as scraper:
        sale = await scraper.get_game_sale(SteamURL("https://store.steampowered.com/app/99/"), NOW)
    assert sale is ScrapeFailure.PAGE_UNAVAILABLE


async def test_search_yields_sales_at_or_above_the_threshold() -> None:
    async with _scraper() as scraper:
        sales = [sale async for sale in scraper.get_sales_from_search("https://store.steampowered.com/search/", 50)]

    by_id = {sale.id: sale for sale in sales}
    assert sorted(by_id) == [10, 555, 1168660]  # "Cheap" is below the threshold
    assert by_id[10].url == "https://store.steampowered.com/app/10/Free_Game/"  # tracking parameters dropped
    assert by_id[10].final_price == 0.0
    assert by_id[555].properties == frozenset({SaleTypes.BUNDLE})  # bundle keyed by its own ID
    assert by_id[1168660].sale_percent == 90  # hidden discount looked up on the app page
