"""Module to scrap the steam website to find sales."""
from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import requests
from bs4 import BeautifulSoup, Tag
from winter_dragon.bot.config import Config
from winter_dragon.bot.constants import (
    CURRENCY_LABELS,
    DATA_APPID,
    DISCOUNT_FINAL_PRICE,
    DISCOUNT_PERCENT,
    DISCOUNT_PRICES,
    GAME_BUY_AREA,
    SEARCH_GAME_TITLE,
    SINGLE_GAME_TITLE,
)
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.database.tables.steamsale import SteamSale


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from winter_dragon.bot.core.bot import WinterDragon


def price_to_num(s: str) -> float:
    """Convert a price string to a float."""
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return float(s.strip(CURRENCY_LABELS))

class SteamURL(LoggerMixin):
    """Class to handle Steam URLs."""

    def __init__(self, url: str) -> None:
        """Initialize the SteamURL class.

        Args:
        ----
            url (str): Url to extract the id from

        """
        self.url = url

    def get_id_from_game_url(self) -> int:
        """Get an id from a steam game url.

        Args:
        ----
            url (str): Url to extract the id from

        Returns:
        -------
            int: The found id of a game

        """
        # sourcery skip: class-extract-method
        # example: https://store.steampowered.com/app/1168660/Barro_2020/
        regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_game_id, self.url)
        self.logger.debug(f"game id: {matches=}")
        # return first match as int, or 0
        return int(matches[0]) or 0

    def is_valid_game_url(self) -> bool:
        """Find out if a url is for a valid game.

        Args:
        ----
            url (str): Url to check for

        Returns:
        -------
            bool: True, False

        """
        return bool(self.get_id_from_game_url())

    def __repr__(self) -> str:
        """Return the url as a string."""
        return self.url

    def __str__(self) -> str:
        """Return the url as a string."""
        return self.url


class SteamScraper(LoggerMixin):
    """Scrape Steam sales. from their website using a set url."""

    search_url = Config(default="https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1&supportedlang=english")

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

        return SteamSale(
            id = url.get_id_from_game_url(),
            title = title.get_text(),
            url = str(url),
            sale_percent = sale_perc.text[1:-1], # strip '-' and '%' from sale tag
            final_price = price_to_num(price.get_text()[:-1].replace(",", ".")),
            is_dlc = bool(soup.find("div", class_="content")),
            is_bundle = False,
            update_datetime = datetime.now(tz=UTC),
        )

    async def get_sales_from_steam(self, percent: int) -> AsyncGenerator[SteamSale | None]:
        """Scrape sales from https://store.steampowered.com/search/.

        With the search options: Ascending price, Special deals, English.
        """
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

        discount = int(discount_perc.text[1:-1]) # strip the - and % from the tag

        if discount < percent:
            return None
        price = price.get_text()[:-1]
        price = price.replace(",", ".")
        title = title.get_text()
        return SteamSale(
            id = int(str(app_id)),
            title = title,
            url = str(url),
            sale_percent = discount,
            final_price = price_to_num(price),
            is_dlc = False,
            is_bundle = False,
            update_datetime = datetime.now(tz=UTC),
        )


async def setup(_bot: WinterDragon) -> None:
    """Set up the SteamScraper."""
    return
