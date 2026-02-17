"""Worker tasks for Steam sales scraping.

These tasks are executed by RQ workers and can run independently
of the main Discord bot process.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TypedDict

from herogold.log.logging import getLogger
from sqlmodel import Session, select

from winter_dragon.bot.extensions.user.steam.sale_scraper import SteamScraper
from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
from winter_dragon.database.constants import engine
from winter_dragon.database.tables.steamsale import SteamSale


logger = getLogger("SteamScraperTasks")


class SaleDictData(TypedDict):
    """Dictionary representation of a Steam sale."""

    app_id: int | None
    title: str
    sale_percent: int
    final_price: float
    url: str


class ScrapingStats(TypedDict):
    """Statistics from a scraping operation."""

    total_scraped: int
    new_count: int
    updated_count: int
    skipped_count: int
    percent: int
    timestamp: str


class ScrapingResult(TypedDict):
    """Result from a Steam scraping operation."""

    new_sales: list[SaleDictData]
    stats: ScrapingStats


class SteamScraperTasks:
    """Steam scraper tasks for worker processing."""

    @staticmethod
    def scrape_steam_sales(percent: int, outdated_delta: int) -> ScrapingResult:
        """Scrape Steam sales and return new sales data.

        This is a synchronous wrapper that workers can execute.
        It runs the async scraping in a new event loop.

        Args:
            percent: Minimum sale percentage to scrape (0-100)
            outdated_delta: Time in seconds when a sale is considered outdated

        Returns:
            ScrapingResult: Results containing new sales and statistics

        """
        logger.info(f"Worker starting Steam sales scrape for {percent}% discount")

        # Create new event loop for this worker
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(SteamScraperTasks._async_scrape_steam_sales(percent, outdated_delta))
        finally:
            loop.close()

    @staticmethod
    async def _async_scrape_steam_sales(percent: int, outdated_delta: int) -> ScrapingResult:
        """Async implementation of Steam sales scraping.

        Args:
            percent: Minimum sale percentage to scrape
            outdated_delta: Time in seconds when a sale is considered outdated

        Returns:
            ScrapingResult: Results with new_sales list and stats

        """
        session = Session(engine)
        scraper = SteamScraper()
        new_sales: list[SaleDictData] = []
        skipped_count = 0
        updated_count = 0

        try:
            # Get existing sales from database
            known_sales = session.exec(select(SteamSale)).all()
            logger.debug(f"Found {len(known_sales)} existing sales in database")

            # Scrape new sales from Steam
            async for sale in scraper.get_sales_from_steam(percent=percent):
                if sale is None:
                    skipped_count += 1
                    continue

                # Update or add the sale
                sale.update()
                updated_count += 1

                # Check if this is outdated (needs notification)
                existing_sale = session.exec(select(SteamSale).where(SteamSale.url == sale.url)).first()

                if not existing_sale or existing_sale.is_outdated(outdated_delta):
                    # Add to new_sales for notification
                    new_sales.append(
                        {
                            "app_id": sale.app_id,
                            "title": sale.title,
                            "sale_percent": sale.sale_percent,
                            "final_price": sale.final_price,
                            "url": sale.url,
                        }
                    )

            session.commit()

        except Exception:
            session.rollback()
            logger.exception("Error during scraping")
            raise
        else:
            result: ScrapingResult = {
                "new_sales": new_sales,
                "stats": {
                    "total_scraped": updated_count + skipped_count,
                    "new_count": len(new_sales),
                    "updated_count": updated_count,
                    "skipped_count": skipped_count,
                    "percent": percent,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }

            logger.info(f"Scraping completed: {len(new_sales)} new sales, {skipped_count} skipped")

            return result
        finally:
            session.close()

    @staticmethod
    def scrape_single_game(url: str) -> SaleDictData | None:
        """Scrape a single game from Steam.

        Args:
            url: Steam game URL

        Returns:
            SaleDictData | None: Game sale data or None if not found

        """
        logger.info(f"Worker scraping single game: {url}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(SteamScraperTasks._async_scrape_single_game(url))
        finally:
            loop.close()

    @staticmethod
    async def _async_scrape_single_game(url: str) -> SaleDictData | None:
        """Async implementation of single game scraping.

        Args:
            url: Steam game URL

        Returns:
            SaleDictData | None: Game sale data

        """
        session = Session(engine)
        scraper = SteamScraper()

        try:
            steam_url = SteamURL(url)
            sale = await scraper.get_game_sale(steam_url)

            if sale is None:
                return None

            # Update the sale in database
            sale.update()
            session.commit()

        except Exception:
            session.rollback()
            logger.exception(f"Error scraping game {url}")
            return None
        else:
            return {
                "app_id": sale.app_id,
                "title": sale.title,
                "sale_percent": sale.sale_percent,
                "final_price": sale.final_price,
                "url": sale.url,
            }
        finally:
            session.close()


# Export functions that RQ workers will call
scrape_steam_sales = SteamScraperTasks.scrape_steam_sales
scrape_single_game = SteamScraperTasks.scrape_single_game
