"""Scraper utilities for Steam bundle listings."""

from __future__ import annotations


class BundleScraper(BaseScraper):
    """Scraper for Steam bundle pages (store.steampowered.com/bundle/<id> or store.steampowered.com/sub/<id>)."""

    async def get_games_from_bundle(self, url: SteamURL) -> AsyncGenerator[SteamURL]:
        """Get all games from a steam bundle page.

        Args:
        ----
            url (SteamURL): URL of the Steam bundle

        Yields:
        ------
            SteamURL: URLs of individual games in the bundle

        """
        html = await self._get_html(str(url))
        soup = BeautifulSoup(html.text, "html.parser")

        item_container = soup.find(class_=BUNDLE_ITEM_CONTAINER)
        if item_container is None:
            self.logger.warning(f"Bundle container not found for {url=}")
            return

        items = item_container.find_all(class_=BUNDLE_ITEM)

        for item in items:
            app_id = item.get(DATA_APPID)
            if app_id is None:
                self.logger.warning(f"App ID not found for bundle item in {url=}")
                continue
            yield SteamURL(f"https://store.steampowered.com/app/{app_id}/")
