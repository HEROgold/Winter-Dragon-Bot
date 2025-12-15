import asyncio

import requests
from herogold.log import LoggerMixin


class BaseScraper(LoggerMixin):
    """Base class for all Steam scrapers with common functionality."""

    def __init__(self) -> None:
        """Initialize the BaseScraper."""
        self.loop = asyncio.get_event_loop()

    async def _get_html(self, url: str) -> requests.Response:
        """Fetch HTML content from a URL.

        Args:
        ----
            url (str): URL to fetch

        Returns:
        -------
            requests.Response: HTTP response object

        """
        return await self.loop.run_in_executor(None, requests.get, url)
