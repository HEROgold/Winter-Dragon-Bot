"""Module to scrap the steam website to find sales."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from herogold.log import LoggerMixin

from winter_dragon.bot.core.config import Config
from winter_dragon.bot.extensions.user.steam.app_scraper import AppScraper
from winter_dragon.bot.extensions.user.steam.bundle_scraper import BundleScraper
from winter_dragon.bot.extensions.user.steam.search_scraper import SearchScraper


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
    from winter_dragon.database.tables.steamsale import SteamSale


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
