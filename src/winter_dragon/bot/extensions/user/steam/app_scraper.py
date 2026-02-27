"""Scrapers for individual Steam store app pages."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Tag
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties

from winter_dragon.bot.extensions.user.steam.base_scraper import BaseScraper
from winter_dragon.bot.extensions.user.steam.tags import (
    DISCOUNT_FINAL_PRICE,
    DISCOUNT_PERCENT,
    GAME_BUY_AREA,
    SINGLE_GAME_TITLE,
    price_to_num,
)


if TYPE_CHECKING:
    from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL


class AppScraper(BaseScraper):
    """Scraper for individual Steam app pages (store.steampowered.com/app/<id>)."""

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

        sale_id = url.app_id
        steam_sale = SteamSale(
            id=sale_id,
            title=title.get_text(),
            url=str(url),
            sale_percent=sale_perc.text[1:-1],  # strip '-' and '%' from sale tag
            final_price=price_to_num(price.get_text()[:-1].replace(",", ".")),
            update_datetime=datetime.now(tz=UTC),
        )
        # TODO: Schedule a re-check for this sale to a ~minute after the app-page mentions the sale ending!
        self.logger.info(f"SteamSale found: {steam_sale=}")
        if bool(soup.find("div", class_="content")):
            SteamSaleProperties(steam_sale_id=sale_id, property=SaleTypes.DLC)
        return steam_sale
