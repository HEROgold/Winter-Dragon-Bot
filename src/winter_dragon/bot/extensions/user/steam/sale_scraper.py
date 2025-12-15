"""Module to scrap the steam website to find sales."""
from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import requests
from bs4 import BeautifulSoup, Tag
from herogold.log import LoggerMixin

from winter_dragon.bot.core.config import Config
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


DISCOUNT_FINAL_PRICE = "discount_final_price"
DISCOUNT_PERCENT = "discount_pct"
SEARCH_GAME_TITLE = "title"
DATA_APPID = "data-ds-appid"
DISCOUNT_PRICES = "discount_prices"
GAME_BUY_AREA = "game_area_purchase_game_wrapper"
SINGLE_GAME_TITLE = "apphub_AppName"
GAME_RELEVANT = "block responsive_apppage_details_right heading responsive_hidden"
IS_DLC_RELEVANT_TO_YOU = "Is this DLC relevant to you?"
BUNDLE_TITLE = "pageheader"
BUNDLE_LINK = "tab_item_overlay"
BUNDLE_PRICE = "price bundle_final_package_price"
BUNDLE_DISCOUNT = "price bundle_discount"
BUNDLE_FINAL_PRICE = "price bundle_final_price_with_discount"
CURRENCY_LABELS = "-$€£¥₣₹د.كد.ك﷼₻₽₾₺₼₸₴₷฿원₫₮₯₱₳₵₲₪₰()"

def price_to_num(s: str) -> float:
    """Convert a price string to a float."""
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return float(s.strip(CURRENCY_LABELS))

# FIXME ValueError: invalid literal for int() with base 10: '357070,366420,546090,701470,1836120'
class SteamURL(LoggerMixin):
    """Class to handle Steam URLs."""

    def __init__(self, url: str) -> None:
        """Initialize the SteamURL class.

        Args:
        ----
            url (str): Url to extract the id from

        """
        self.url = url
        self._id = None

    @property
    def id(self) -> int:
        """Get an id from a steam game url.

        Args:
        ----
            url (str): Url to extract the id from

        Returns:
        -------
            int: The found id of a game

        """
        if self._id:
            return self._id
        # example: https://store.steampowered.com/app/1168660/Barro_2020/
        regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_game_id, self.url)
        self.logger.debug(f"game id: {matches=}, {matches=}")
        self._id = int(matches[0]) if matches else 0
        return self._id

    def is_valid_game_url(self) -> bool:
        """Find out if a url is for a valid game.

        Args:
        ----
            url (str): Url to check for

        """
        return bool(self.id)

    def __repr__(self) -> str:
        """Return the url as a string."""
        return self.url

    def __str__(self) -> str:
        """Return the url as a string."""
        return self.url

class AppScraper(LoggerMixin):
    """Scraper for individual Steam app pages (store.steampowered.com/app/<id>)."""

    def __init__(self) -> None:
        """Initialize the AppScraper."""
        self.loop = asyncio.get_event_loop()

    async def _get_html(self, url: str) -> requests.Response:
        return await self.loop.run_in_executor(None, requests.get, url)

    async def _get_buy_area(self, soup: BeautifulSoup) -> Tag | None:
        add_to_cart = soup.find(class_="btn_addtocart")
        if add_to_cart is None:
            return None
        buy_area = add_to_cart.find_parent(class_=GAME_BUY_AREA)
        return buy_area if isinstance(buy_area, Tag) else None

    async def get_game_sale(self, url: SteamURL) -> SteamSale | None:
        """Get a single game sale from specific url.

        Args:
        ----
            url (SteamURL): URL of the Steam game

        Returns:
        -------
            SteamSale | None: Steam sale information or None if not found

        """
        if not url.is_valid_game_url():
            msg = "Invalid Steam Game URL"
            raise ValueError(msg)

        html = await self._get_html(str(url))
        soup = BeautifulSoup(html.text, "html.parser")

        buy_area = await self._get_buy_area(soup)
        if buy_area is None:
            self.logger.warning(f"Buy area not found for {url=}")
            return None

        sale_perc = buy_area.find(class_=DISCOUNT_PERCENT)
        if not isinstance(sale_perc, Tag):
            self.logger.warning(f"Sale percent not found for {url=}")
            return None
        price = buy_area.find(class_=DISCOUNT_FINAL_PRICE)
        if not isinstance(price, Tag):
            self.logger.warning(f"Price not found for {url=}")
            return None
        title = soup.find(class_=SINGLE_GAME_TITLE)
        if not isinstance(title, Tag):
            self.logger.warning(f"Title not found for {url=}")
            return None

        sale_id = url.id
        steam_sale = SteamSale(
            id = sale_id,
            title = title.get_text(),
            url = str(url),
            sale_percent = sale_perc.text[1:-1], # strip '-' and '%' from sale tag
            final_price = price_to_num(price.get_text()[:-1].replace(",", ".")),
            update_datetime = datetime.now(tz=UTC),
        )
        self.logger.info(f"SteamSale found: {steam_sale=}")
        if bool(soup.find("div", class_="content")):
            SteamSaleProperties(steam_sale_id=sale_id, property=SaleTypes.DLC)
        return steam_sale


class BundleScraper(LoggerMixin):
    """Scraper for Steam bundle pages (store.steampowered.com/bundle/<id> or store.steampowered.com/sub/<id>)."""

    def __init__(self) -> None:
        """Initialize the BundleScraper."""
        self.loop = asyncio.get_event_loop()

    async def _get_html(self, url: str) -> requests.Response:
        return await self.loop.run_in_executor(None, requests.get, url)

    async def get_games_from_bundle(self, url: SteamURL) -> AsyncGenerator[SteamURL]:
        """Get all games from a steam bundle page.

        Args:
        ----
            url (SteamURL): URL of the Steam bundle

        Yields:
        ------
            SteamURL: URLs of individual games in the bundle

        """
        class_ = "package_landing_page_item_list"
        item_tag = "tab_item tablet_list_item"
        app_id_attribute = "data-ds-appid"

        html = await self._get_html(str(url))
        soup = BeautifulSoup(html.text, "html.parser")

        item_container = soup.find(class_=class_)
        if item_container is None:
            self.logger.warning(f"Bundle container not found for {url=}")
            return

        items = item_container.find_all(class_=item_tag)

        for item in items:
            app_id = item.get(app_id_attribute)
            if app_id is None:
                self.logger.warning(f"App ID not found for bundle item in {url=}")
                continue
            yield SteamURL(f"https://store.steampowered.com/app/{app_id}/")


class SearchScraper(LoggerMixin):
    """Scraper for Steam search results (store.steampowered.com/search/)."""

    def __init__(self) -> None:
        """Initialize the SearchScraper."""
        self.loop = asyncio.get_event_loop()
        self.app_scraper = AppScraper()
        self.bundle_scraper = BundleScraper()

    async def _get_html(self, url: str) -> requests.Response:
        return await self.loop.run_in_executor(None, requests.get, url)

    async def get_sales_from_search(self, search_url: str, percent: int) -> AsyncGenerator[SteamSale | None]:
        """Scrape sales from a Steam search URL.

        Args:
        ----
            search_url (str): URL of the Steam search page
            percent (int): Minimum sale percentage to filter

        Yields:
        ------
            SteamSale | None: Steam sale information or None if not found

        """
        self.logger.debug(f"Scraping Steam sales: {percent=}")
        html = await self._get_html(search_url)
        soup = BeautifulSoup(html.text, "html.parser")

        for sale_tag in soup.find_all(class_=DISCOUNT_PRICES):
            if not isinstance(sale_tag, Tag): # pyright: ignore[reportUnnecessaryIsInstance]
                self.logger.warning(f"Sale tag not found for {sale_tag=}, Expected Tag, got {type(sale_tag)}")
                continue
            yield await self.get_sale_from_search(sale_tag, percent)

    async def get_sale_from_search(self, sale_tag: Tag, percent: int) -> SteamSale | None:
        """Get a single sale from the steam search page.

        Args:
        ----
            sale_tag (Tag): BeautifulSoup tag containing sale information
            percent (int): Minimum sale percentage to filter

        Returns:
        -------
            SteamSale | None: Steam sale information or None if not found

        """
        a_tag = sale_tag.find_parent("a", href=True)

        if not isinstance(a_tag, Tag):
            self.logger.warning(f"Tag not found for {sale_tag=}. Expected Tag got, {type(a_tag)}")
            return None
        price = a_tag.find(class_=DISCOUNT_FINAL_PRICE)
        title = a_tag.find(class_=SEARCH_GAME_TITLE)
        app_id = a_tag.get(DATA_APPID)
        url = a_tag.get("href")
        if not isinstance(price, Tag) or not isinstance(title, Tag):
            self.logger.warning(f"Price or title not found for {sale_tag=}, Expected Tag, got {type(price)}")
            return None

        if sale_tag.parent is None:
            self.logger.warning(f"Sale tag parent not found for {sale_tag=}")
            return None
        # Can sale_tag.parent be a_tag?
        discount_perc = sale_tag.parent.find(class_=DISCOUNT_PERCENT)

        if discount_perc is None: # Check game's page
            return await self.app_scraper.get_game_sale(SteamURL(str(url)))

        sale_percentage = int(discount_perc.text[1:-1]) # strip the - and % from the tag

        if sale_percentage < percent:
            self.logger.debug(f"{sale_percentage=} is lower than target {percent=}, skipping")
            return None

        price = price.get_text()[:-1]
        price = price.replace(",", ".")
        title = title.get_text()
        self.logger.debug(f"SteamSale found: {url=}, {title=}, {price=}, {sale_percentage=}, {app_id=}")

        if "sub" in str(url) or "bundle" in str(url):
            # Note: .com/sub/    is used in searchable bundles. As seen in https://store.steampowered.com/sub/66335
            # Note: .com/bundle/ is used for game related bundles. Seen in https://store.steampowered.com/bundle/62652
            self.logger.debug(f"Found bundle or sub: {url=}, processing bundle items")
            async for item in self.bundle_scraper.get_games_from_bundle(SteamURL(str(url))):
                self.logger.debug(f"Processing bundle item: {item=}")
            SteamSaleProperties(steam_sale_id=int(str(app_id)), property=SaleTypes.BUNDLE)
            return SteamSale(
                id = int(str(app_id).split(",")[0]),
                title = title,
                url = str(url),
                sale_percent = sale_percentage,
                final_price = price_to_num(price),
                update_datetime = datetime.now(tz=UTC),
            )

        return SteamSale(
            id = int(str(app_id)),
            title = title,
            url = str(url),
            sale_percent = sale_percentage,
            final_price = price_to_num(price),
            update_datetime = datetime.now(tz=UTC),
        )


class BrowseScraper(LoggerMixin):
    """Scraper for Steam browse results (store.steampowered.com).

    Note: This is a placeholder for future browse functionality.
    Currently not used by the main SteamScraper.
    """

    def __init__(self) -> None:
        """Initialize the BrowseScraper."""
        self.loop = asyncio.get_event_loop()

    async def _get_html(self, url: str) -> requests.Response:
        return await self.loop.run_in_executor(None, requests.get, url)

class SteamScraper(LoggerMixin):
    """Scrape Steam sales from their website using a set url.

    This class now delegates to specialized scrapers for better separation of concerns.
    """

    search_url = Config("https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1&supportedlang=english")

    def __init__(self) -> None:
        """Initialize the SteamScraper."""
        self.loop = asyncio.get_event_loop()
        self.search_scraper = SearchScraper()
        self.app_scraper = AppScraper()
        self.bundle_scraper = BundleScraper()

    async def get_game_sale(self, url: SteamURL) -> SteamSale | None:
        """Get a single game sale from specific url.

        Args:
        ----
            url (SteamURL): URL of the Steam game

        Returns:
        -------
            SteamSale | None: Steam sale information or None if not found

        """
        return await self.app_scraper.get_game_sale(url)

    async def get_sales_from_steam(self, percent: int) -> AsyncGenerator[SteamSale | None]:
        """Scrape sales from https://store.steampowered.com/search/.

        With the search options: Ascending price, Special deals, English.

        Args:
        ----
            percent (int): Minimum sale percentage to filter

        Yields:
        ------
            SteamSale | None: Steam sale information or None if not found

        """
        async for sale in self.search_scraper.get_sales_from_search(self.search_url, percent):
            yield sale

    async def get_games_from_bundle(self, url: SteamURL) -> AsyncGenerator[SteamURL]:
        """Get all games from a steam bundle page.

        Args:
        ----
            url (SteamURL): URL of the Steam bundle

        Yields:
        ------
            SteamURL: URLs of individual games in the bundle

        """
        async for game_url in self.bundle_scraper.get_games_from_bundle(url):
            yield game_url
