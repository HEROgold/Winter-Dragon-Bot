"""Module to scrap the steam website to find sales."""
from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import requests
from bs4 import BeautifulSoup, Tag
from winter_dragon.bot.config import Config
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from winter_dragon.bot.core.bot import WinterDragon

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


class SteamScraper(LoggerMixin):
    """Scrape Steam sales. from their website using a set url."""

    search_url = Config("https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1&supportedlang=english")

    def __init__(self) -> None:
        """Initialize the SteamScraper."""
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
        """Get a single game sale from specific url."""
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

        self.logger.info(f"SteamSale found: {url=}, {title=}, {price=}, {sale_perc=}")
        sale_id = url.id
        sale = SteamSale(
            id = sale_id,
            title = title.get_text(),
            url = str(url),
            sale_percent = sale_perc.text[1:-1], # strip '-' and '%' from sale tag
            final_price = price_to_num(price.get_text()[:-1].replace(",", ".")),
            update_datetime = datetime.now(tz=UTC),
        )
        if bool(soup.find("div", class_="content")):
            SteamSaleProperties(steam_sale_id=sale_id, property=SaleTypes.DLC)

        self.logger.debug(f"SteamSale found: {url=}, {title=}, {price=}")
        return sale

    async def get_sales_from_steam(self, percent: int) -> AsyncGenerator[SteamSale | None]:
        """Scrape sales from https://store.steampowered.com/search/.

        With the search options: Ascending price, Special deals, English.
        """
        self.logger.debug(f"Scraping Steam sales: {percent=}")
        html = await self._get_html(self.search_url)
        soup = BeautifulSoup(html.text, "html.parser")

        for sale_tag in soup.find_all(class_=DISCOUNT_PRICES):
            if not isinstance(sale_tag, Tag):
                self.logger.warning(f"Sale tag not found for {sale_tag=}, Expected Tag, got {type(sale_tag)}")
                continue
            yield await self.get_sale_from_steam(sale_tag, percent)


    async def get_sale_from_steam(self, sale_tag: Tag, percent: int) -> SteamSale | None:
        """Get a single sale from the steam search page."""
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
            return await self.get_game_sale(SteamURL(str(url)))

        sale_percentage = int(discount_perc.text[1:-1]) # strip the - and % from the tag

        if sale_percentage < percent:
            self.logger.debug(f"{sale_percentage=} is lower than target {percent=}, skipping")
            return None

        price = price.get_text()[:-1]
        price = price.replace(",", ".")
        title = title.get_text()
        self.logger.debug(f"SteamSale found: {url=}, {title=}, {price=}, {sale_percentage=}, {app_id=}")

        # TODO: Mark as bundle, if multiple app ids
        # TODO: regex the url sub/(\d+)/ to determine if bundle
        # if "," in app_id:
        #     # url: sub/66335 # bundle of multiple ga,es with id.
        #     SteamSaleProperties(steam_sale_id=sale_id, property=SaleTypes.DLC)
        #     # Sale for multiple games, should be a bundle
        #     sale = SteamSale(
        #         id = int(str(app_id).split(",")[0]),
        #         title = title,
        #         url = str(url),
        #         sale_percent = sale_percentage,
        #         final_price = price_to_num(price),
        #         update_datetime = datetime.now(tz=UTC),
        #     )

        return SteamSale(
            id = int(str(app_id)),
            title = title,
            url = str(url),
            sale_percent = sale_percentage,
            final_price = price_to_num(price),
            update_datetime = datetime.now(tz=UTC),
        )


async def setup(_bot: WinterDragon) -> None:
    """Set up the SteamScraper."""
    return
