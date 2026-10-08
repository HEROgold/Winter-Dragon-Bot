"""The /steam command group, its page buttons, and the background scrape of Steam's specials."""

from __future__ import annotations

lazy import asyncio
lazy from datetime import UTC, datetime, timedelta
lazy from typing import TYPE_CHECKING, override

lazy from sqlmodel import Session, SQLModel
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_config.steam import SteamSettings

lazy from winter_dragon.cogs.steam.models import STEAM_TABLES, SteamUsers
lazy from winter_dragon.cogs.steam.notifier import SteamSaleNotifier
lazy from winter_dragon.cogs.steam.pages import build_page, page_buttons, page_count
lazy from winter_dragon.cogs.steam.scrapers import ScrapedSale, ScrapeFailure, SteamScraper
lazy from winter_dragon.cogs.steam.store import SteamSaleStore
lazy from winter_dragon.cogs.steam.throttle import RequestThrottle


if TYPE_CHECKING:
    lazy from collections.abc import Coroutine, Generator, Iterable

    lazy from sqlalchemy import Connection, Engine
    lazy from wd_discord.gateway.events import CommandInteraction, ComponentInteraction

    lazy from winter_dragon.cogs.steam.models import SteamSale


DEFAULT_THRESHOLD = 100
"""The discount /steam show lists by default, and a new subscriber's threshold: free games only."""
MAX_PERCENT = 100
MIN_SLEEP_SECONDS = 60.0
"""The loop never sleeps less than this, so a failing re-check is retried at most once a minute."""
SALE_END_HOUR_UTC = 17
"""The hour (UTC) Steam starts and ends most sales: 10:00 Pacific during daylight saving time."""
ROLLOVER_GRACE = timedelta(minutes=5)
"""How long after Steam's daily rollover the extra scrape runs, giving the store time to update."""


def next_scrape_time(now: datetime, interval: timedelta) -> datetime:
    """Return when to scrape next: after ``interval``, or just after Steam's daily rollover if that comes first.

    Steam starts and ends most sales at the rollover (:data:`SALE_END_HOUR_UTC`), so scraping right after it picks up
    new sales the same day instead of up to ``interval`` later.
    """
    rollover = now.replace(hour=SALE_END_HOUR_UTC, minute=0, second=0, microsecond=0) + ROLLOVER_GRACE
    if rollover <= now:
        rollover += timedelta(days=1)
    return min(now + interval, rollover)


def sale_queries(percent: int, complete_percent: int, top_sellers: int) -> Generator[tuple[int, int | None]]:
    """Yield the ``(percent, limit)`` of each query a scrape makes.

    That's every sale from ``complete_percent`` up, then the ``top_sellers`` best-selling ones from ``percent`` up,
    when that's lower.
    """
    yield max(percent, complete_percent), None
    if percent < complete_percent:
        yield percent, top_sellers


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)


class SteamSales(GroupCog, name="steam", description="Get notified about free and discounted Steam games"):
    """Lists Steam sales on request and DMs subscribers new ones, re-checking sales right after they end."""

    _task: asyncio.Task[None] | None = None
    _throttle: RequestThrottle | None = None

    @property
    def throttle(self) -> RequestThrottle:
        """The request throttle every scraper of this cog shares, so spacing and rate-limit pauses span them all."""
        if self._throttle is None:
            self._throttle = RequestThrottle(SteamSettings.request_interval)
        return self._throttle

    @property
    def _bind(self) -> Engine | Connection:
        """The database the cog's sessions connect to."""
        return self.session.get_bind()

    @property
    def _outdated_after(self) -> timedelta:
        return timedelta(seconds=SteamSettings.outdated_after)

    @property
    def _recheck_delay(self) -> timedelta:
        return timedelta(seconds=SteamSettings.recheck_delay)

    @override
    async def load(self) -> None:
        """Create the Steam tables if missing, then start the background scrape loop."""
        tables = [SQLModel.metadata.tables[model.__name__.lower()] for model in STEAM_TABLES]
        SQLModel.metadata.create_all(self._bind, tables=tables)
        self._task = self.bot.loop.create_task(self._run())

    @override
    async def unload(self) -> None:
        """Stop the background scrape loop."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        await super().unload()

    async def _run(self) -> None:
        """Scrape on load, then on :func:`next_scrape_time`, and re-check sales just after they end, forever."""
        next_scrape = utc_now()
        while True:
            now = utc_now()
            if now >= next_scrape:
                await self._guarded(self.scrape(now))
                next_scrape = next_scrape_time(utc_now(), timedelta(seconds=SteamSettings.update_interval))
                self.logger.info(t"Next Steam scrape at {next_scrape:%Y-%m-%d %H:%M} UTC")
            await self._guarded(self.recheck_due(utc_now()))
            with Session(self._bind) as session:
                next_recheck = SteamSaleStore(session).next_recheck(delay=self._recheck_delay)
            wake = min(next_scrape, next_recheck) if next_recheck is not None else next_scrape
            await asyncio.sleep(max(MIN_SLEEP_SECONDS, (wake - utc_now()).total_seconds()))

    async def _guarded(self, work: Coroutine[object, object, None]) -> None:
        """Run ``work``, logging instead of raising, so one failed run never stops the loop."""
        try:
            await work
        except Exception:
            self.logger.exception(t"Steam background work failed")

    async def scrape(self, now: datetime) -> None:
        """Ask Steam for its sales, store them, and DM subscribers new ones.

        Stores every sale from :attr:`SteamSettings.complete_percent` up, and the
        :attr:`SteamSettings.top_sellers` best-selling ones below it, down to :attr:`SteamSettings.stored_percent`
        or a lower subscriber threshold, so /steam show and every subscriber find their sales. Shown sales this
        scrape didn't list (ended, or no longer among the top sellers) are checked again, unless their end is
        known: those are re-checked when they end, by :meth:`recheck_due`.
        """
        with Session(self._bind) as session:
            store = SteamSaleStore(session)
            lowest = store.lowest_threshold()
            percent = SteamSettings.stored_percent if lowest is None else min(SteamSettings.stored_percent, lowest)
            seen: set[int] = set()
            sent_before = self.throttle.sent
            async with SteamScraper(throttle=self.throttle, country_code=SteamSettings.country_code) as scraper:
                for query_percent, limit in sale_queries(percent, SteamSettings.complete_percent, SteamSettings.top_sellers):
                    async for scraped in scraper.query_sales(query_percent, limit):
                        if scraped.id not in seen:
                            seen.add(scraped.id)
                            store.record(scraped, now=now, outdated_after=self._outdated_after)
                if seen:  # finding nothing means Steam failed, not that every sale ended
                    unseen = store.unseen_without_end(now, percent, outdated_after=self._outdated_after)
                    await self._recheck(scraper, store, unseen, now)
            notified = await SteamSaleNotifier(self.bot.client, store, color=SteamSettings.embed_color).notify(
                now=now,
                content=self._notification_content(),
            )
            requests = self.throttle.sent - sent_before
            self.logger.info(
                t"Steam scrape done (threshold {percent} percent, {len(seen)} sales, {requests} requests), "
                t"notified {notified} subscriber(s)",
            )

    async def recheck_due(self, now: datetime) -> None:
        """Check the sales whose announced end has passed: update those still running, remove those that ended."""
        with Session(self._bind) as session:
            store = SteamSaleStore(session)
            due = store.due_rechecks(now=now, delay=self._recheck_delay)
            if not due or self.throttle.paused:
                return
            async with SteamScraper(throttle=self.throttle, country_code=SteamSettings.country_code) as scraper:
                await self._recheck(scraper, store, due, now)

    async def _recheck(self, scraper: SteamScraper, store: SteamSaleStore, sales: Iterable[SteamSale], now: datetime) -> None:
        """Check ``sales`` on Steam: update those still running, remove those that ended, retry later on failure."""
        by_item = {item: sale for sale in sales if (item := sale.steam_url.store_item) is not None}
        async for item, details in scraper.get_sales(by_item):
            sale = by_item[item]
            match details:
                case ScrapeFailure():
                    self.logger.warning(t"Could not re-check {sale.url}; trying again later")
                case ScrapedSale():
                    store.refresh(sale, details, now=now)
                case None:
                    self.logger.info(t"Steam sale ended: {sale.title}")
                    store.remove(sale)

    def _notification_content(self) -> str:
        """Return the text above a sale DM, pointing at the commands to stop notifications and see every sale."""
        return (
            f"Use {self.mention(self.remove)} to stop these notifications.\n"
            f"Use {self.mention(self.show)} to see every current sale."
        )

    @Cog.command(name="add", description="Get notified automatically about free steam games")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def add(self, interaction: CommandInteraction) -> None:
        """Subscribe the invoking user to Steam sale DMs."""
        user = interaction.invoking_user
        if user is None:
            return
        with Session(self._bind) as session:
            if SteamSaleStore(session).subscriber(int(user.id)) is not None:
                await self.bot.client.create_interaction_response(
                    interaction,
                    content="Already in the list of recipients",
                    ephemeral=True,
                )
                return
            session.add(SteamUsers(id=int(user.id), last_notification=utc_now()))
            session.commit()
        await self.bot.client.create_interaction_response(
            interaction,
            content=f"I will notify you of new steam games!\nUse {self.mention(self.show)} to view current sales.",
            ephemeral=True,
        )

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="percentage",
        description="Get notified of steam games on sale for the given percentage or higher",
    )
    async def percentage(self, interaction: CommandInteraction, percent: int) -> None:
        """Set the minimum discount the invoking user is notified about."""
        user = interaction.invoking_user
        if user is None:
            return
        if not 0 <= percent <= MAX_PERCENT:
            await self.bot.client.create_interaction_response(
                interaction,
                content=f"The percentage must be between 0 and {MAX_PERCENT}.",
                ephemeral=True,
            )
            return
        with Session(self._bind) as session:
            subscriber = SteamSaleStore(session).subscriber(int(user.id))
            if subscriber is not None:
                subscriber.sale_threshold = percent
                session.add(subscriber)
                session.commit()
        if subscriber is None:
            content = f"You are not in the list of recipients. Use {self.mention(self.add)} to subscribe."
        else:
            content = f"Changed your sale notification threshold to {percent}%."
        await self.bot.client.create_interaction_response(interaction, content=content, ephemeral=True)

    @Cog.command(name="remove", description="No longer get notified of free steam games")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def remove(self, interaction: CommandInteraction) -> None:
        """Unsubscribe the invoking user from Steam sale DMs."""
        user = interaction.invoking_user
        if user is None:
            return
        with Session(self._bind) as session:
            subscriber = SteamSaleStore(session).subscriber(int(user.id))
            if subscriber is not None:
                session.delete(subscriber)
                session.commit()
        content = "Not in the list of recipients" if subscriber is None else "I will no longer notify you of new steam games."
        await self.bot.client.create_interaction_response(interaction, content=content, ephemeral=True)

    @Cog.command(  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
        name="show",
        description="Get a list of steam games that are on sale for the given percentage or higher",
    )
    async def show(self, interaction: CommandInteraction, percent: int = DEFAULT_THRESHOLD) -> None:
        """Show the first page of current sales of at least ``percent``, with buttons to page through them."""
        user = interaction.invoking_user
        if user is None:
            return
        with Session(self._bind) as session:
            store = SteamSaleStore(session)
            sales = store.current_sales(percent, now=utc_now(), outdated_after=self._outdated_after)
            if not sales:
                await self.bot.client.create_interaction_response(
                    interaction,
                    content=f"No steam games found with sales {percent}% or higher.",
                    ephemeral=True,
                )
                return
            await self.bot.client.defer_interaction(interaction)
            embed = build_page(sales, store.properties(sales), page=0, color=SteamSettings.embed_color)
        buttons = page_buttons(self.show_page, owner_id=int(user.id), percent=percent, page=0, pages=page_count(len(sales)))
        await self.bot.client.edit_original_interaction_response(interaction, embeds=[embed], components=buttons)

    @Cog.component("steam-show")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def show_page(self, interaction: ComponentInteraction, owner_id: str, percent: str, page: str) -> None:
        """Turn a /steam show listing to ``page``; only the user who ran the command may."""
        user = interaction.invoking_user
        if user is None or str(user.id) != owner_id:
            await self.bot.client.create_interaction_response(
                interaction,
                content=(
                    "Only the person who ran this command can page through it. "
                    f"Use {self.mention(self.show)} for your own list."
                ),
                ephemeral=True,
            )
            return
        with Session(self._bind) as session:
            store = SteamSaleStore(session)
            sales = store.current_sales(int(percent), now=utc_now(), outdated_after=self._outdated_after)
            pages = page_count(len(sales))
            target = min(max(int(page), 0), pages - 1)
            embed = build_page(sales, store.properties(sales), page=target, color=SteamSettings.embed_color)
        buttons = page_buttons(self.show_page, owner_id=int(owner_id), percent=int(percent), page=target, pages=pages)
        await self.bot.client.update_interaction_message(interaction, embeds=[embed], components=buttons)
