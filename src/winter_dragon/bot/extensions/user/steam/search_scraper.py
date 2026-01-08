"""Scraper utilities for Steam search result pages."""

from collections import Counter, defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bs4 import BeautifulSoup, Tag

from winter_dragon.bot.extensions.user.steam.app_scraper import AppScraper
from winter_dragon.bot.extensions.user.steam.base_scraper import BaseScraper
from winter_dragon.bot.extensions.user.steam.bundle_scraper import BundleScraper
from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
from winter_dragon.bot.extensions.user.steam.tags import (
    DATA_APPID,
    DISCOUNT_FINAL_PRICE,
    DISCOUNT_PERCENT,
    DISCOUNT_PRICES,
    SEARCH_GAME_TITLE,
    price_to_num,
)
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties


@dataclass
class SkipSample:
    """Diagnostic sample for a skipped sale."""

    url: str | None
    title: str | None
    sale_percentage: int | None
    extra: str | None = None


@dataclass
class SteamSearchDiagnostics:
    """Aggregate diagnostic information for a search scrape run."""

    percent_threshold: int
    examined: int = 0
    yielded: int = 0
    skip_counts: Counter[str] = field(default_factory=Counter)
    skip_samples: dict[str, list[SkipSample]] = field(default_factory=lambda: defaultdict(list))
    sample_limit: int = 5

    def record_examined(self) -> None:
        """Increment the number of examined sale tags."""
        self.examined += 1

    def record_yield(self, *, url: str | None, title: str | None, sale_percentage: int | None) -> None:
        """Record a successful sale extraction."""
        self.yielded += 1

    def record_skip(
        self,
        reason: str,
        *,
        url: str | None = None,
        title: str | None = None,
        sale_percentage: int | None = None,
        extra: str | None = None,
    ) -> None:
        """Record a skipped sale along with optional context."""
        self.skip_counts[reason] += 1
        samples = self.skip_samples[reason]
        if len(samples) < self.sample_limit:
            samples.append(SkipSample(url=url, title=title, sale_percentage=sale_percentage, extra=extra))

    def emit(self, logger) -> None:
        """Write the aggregated diagnostics to the provided logger."""
        total_skipped = sum(self.skip_counts.values())
        logger.info(
            "Steam search summary: examined=%s yielded=%s skipped=%s threshold=%s",
            self.examined,
            self.yielded,
            total_skipped,
            self.percent_threshold,
        )
        if not self.skip_counts:
            return
        breakdown = ", ".join(f"{reason}={count}" for reason, count in self.skip_counts.items())
        logger.debug(f"Skip breakdown: {breakdown}")
        for reason, samples in self.skip_samples.items():
            for sample in samples:
                logger.debug(
                    "Skip sample (%s): url=%s title=%s sale_percentage=%s extra=%s",
                    reason,
                    sample.url,
                    sample.title,
                    sample.sale_percentage,
                    sample.extra,
                )


class SearchScraper(BaseScraper):
    """Scraper for Steam search results (store.steampowered.com/search/)."""

    def __init__(self) -> None:
        """Initialize the SearchScraper."""
        super().__init__()
        self.app_scraper = AppScraper()
        self.bundle_scraper = BundleScraper()

    async def get_sales_from_search(self, search_url: str, percent: int) -> AsyncGenerator[SteamSale | None]:
        """Scrape sales from a Steam search URL."""
        diagnostics = SteamSearchDiagnostics(percent_threshold=percent)
        self.logger.debug(f"Scraping Steam sales: {percent=}")
        html = await self._get_html(search_url)
        soup = BeautifulSoup(html.text, "html.parser")

        for sale_tag in soup.find_all(class_=DISCOUNT_PRICES):
            sale = await self.get_sale_from_search(sale_tag, percent, diagnostics)
            yield sale

        diagnostics.emit(self.logger)

    async def get_sale_from_search(
        self,
        sale_tag: Tag,
        percent: int,
        diagnostics: SteamSearchDiagnostics,
    ) -> SteamSale | None:
        """Get a single sale from the steam search page."""
        diagnostics.record_examined()
        a_tag = sale_tag.find_parent("a", href=True)

        if not isinstance(a_tag, Tag):
            diagnostics.record_skip("missing_anchor", extra=f"type={type(a_tag)!r}")
            self.logger.warning(f"Tag not found for {sale_tag=}. Expected Tag got, {type(a_tag)}")
            return None
        price = a_tag.find(class_=DISCOUNT_FINAL_PRICE)
        title = a_tag.find(class_=SEARCH_GAME_TITLE)
        app_id = a_tag.get(DATA_APPID)
        url = a_tag.get("href")
        url_str = str(url) if url else None
        title_text = title.get_text() if isinstance(title, Tag) else None

        if not isinstance(price, Tag) or not isinstance(title, Tag):
            diagnostics.record_skip(
                "missing_price_or_title",
                url=url_str,
                title=title_text,
                extra=f"price_tag={type(price)!r}, title_tag={type(title)!r}",
            )
            self.logger.warning(f"Price or title not found for {sale_tag=}, Expected Tag, got {type(price)}")
            return None
        if url_str is None:
            diagnostics.record_skip("missing_url", title=title_text)
            self.logger.warning(f"URL not found for {sale_tag=}")
            return None
        if app_id is None:
            diagnostics.record_skip("missing_app_id", url=url_str, title=title_text)
            self.logger.warning(f"App ID not found for {sale_tag=} {url_str=}")
            return None

        if sale_tag.parent is None:
            diagnostics.record_skip("missing_discount_container", url=url_str, title=title_text)
            self.logger.warning(f"Sale tag parent not found for {sale_tag=}")
            return None
        # Can sale_tag.parent be a_tag?
        discount_perc = sale_tag.parent.find(class_=DISCOUNT_PERCENT)

        if discount_perc is None:  # Check game's page
            return await self._fetch_from_app_page(SteamURL(url_str), title_text, diagnostics)

        sale_percentage = int(discount_perc.text[1:-1])  # strip the - and % from the tag

        if sale_percentage < percent:
            diagnostics.record_skip(
                "below_threshold",
                url=url_str,
                title=title_text,
                sale_percentage=sale_percentage,
                extra=f"threshold={percent}",
            )
            return None

        price = price.get_text()[:-1]
        price = price.replace(",", ".")
        title_text = title.get_text()
        self.logger.debug(f"SteamSale found: {url_str=}, {title_text=}, {price=}, {sale_percentage=}, {app_id=}")

        if "sub" in url_str or "bundle" in url_str:
            # Note: .com/sub/    is used in searchable bundles. As seen in https://store.steampowered.com/sub/66335
            # Note: .com/bundle/ is used for game related bundles. Seen in https://store.steampowered.com/bundle/62652
            steam_sale = await self._extract_bundle_sale(a_tag, sale_percentage)
        else:
            steam_sale = SteamSale(
                id=int(str(app_id)),
                title=title_text,
                url=url_str,
                sale_percent=sale_percentage,
                final_price=price_to_num(price),
                update_datetime=datetime.now(tz=UTC),
            )

        self._record_sale_success(diagnostics, steam_sale)
        return steam_sale

    async def _extract_bundle_sale(self, a_tag: Tag, sale_percentage: int) -> SteamSale:
        price = a_tag.find(class_=DISCOUNT_FINAL_PRICE)
        title = a_tag.find(class_=SEARCH_GAME_TITLE)
        app_id = a_tag.get(DATA_APPID)
        url = a_tag.get("href")

        self.logger.debug(f"Found bundle or sub: {url=}, processing bundle items")
        async for item in self.bundle_scraper.get_games_from_bundle(SteamURL(str(url))):
            self.logger.debug(f"Processing bundle item: {item=}")
        SteamSaleProperties(steam_sale_id=int(str(app_id)), property=SaleTypes.BUNDLE)
        return SteamSale(
            id=int(str(app_id).split(",")[0]),
            title=title.get_text() or "Bundle",
            url=str(url),
            sale_percent=sale_percentage,
            final_price=price_to_num(price.get_text()) if price else 0.0,
            update_datetime=datetime.now(tz=UTC),
        )

    async def _fetch_from_app_page(
        self,
        steam_url: SteamURL,
        title: str | None,
        diagnostics: SteamSearchDiagnostics,
    ) -> SteamSale | None:
        sale = await self.app_scraper.get_game_sale(steam_url)
        if sale is None:
            diagnostics.record_skip("app_page_lookup_failed", url=str(steam_url), title=title)
            return None
        self._record_sale_success(diagnostics, sale)
        return sale

    @staticmethod
    def _record_sale_success(diagnostics: SteamSearchDiagnostics, sale: SteamSale) -> None:
        try:
            sale_percent = int(sale.sale_percent) if sale.sale_percent is not None else None
        except (TypeError, ValueError):
            sale_percent = None
        diagnostics.record_yield(url=sale.url, title=sale.title, sale_percentage=sale_percent)
