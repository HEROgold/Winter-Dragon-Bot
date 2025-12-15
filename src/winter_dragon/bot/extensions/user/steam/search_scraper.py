from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag

from winter_dragon.bot.extensions.user.steam.app_scraper import AppScraper
from winter_dragon.bot.extensions.user.steam.base_scraper import BaseScraper
from winter_dragon.bot.extensions.user.steam.bundle_scraper import BundleScraper
from winter_dragon.bot.extensions.user.steam.sale_scraper import (
    DATA_APPID,
    DISCOUNT_PERCENT,
    DISCOUNT_PRICES,
    SEARCH_GAME_TITLE,
)
from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
from winter_dragon.bot.extensions.user.steam.tags import DISCOUNT_FINAL_PRICE, price_to_num
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties


class SearchScraper(BaseScraper):
    """Scraper for Steam search results (store.steampowered.com/search/)."""

    def __init__(self) -> None:
        """Initialize the SearchScraper."""
        super().__init__()
        self.app_scraper = AppScraper()
        self.bundle_scraper = BundleScraper()

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
