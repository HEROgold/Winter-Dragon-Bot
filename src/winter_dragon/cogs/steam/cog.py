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


if TYPE_CHECKING:
    lazy from collections.abc import Coroutine

    lazy from sqlalchemy import Connection, Engine
    lazy from wd_discord.gateway.events import CommandInteraction, ComponentInteraction

    lazy from winter_dragon.cogs.steam.models import SteamSale


DEFAULT_THRESHOLD = 100
"""The discount scraped for, and a new subscriber's threshold: free games only."""
MAX_PERCENT = 100
MIN_SLEEP_SECONDS = 60.0
"""The loop never sleeps less than this, so a failing re-check is retried at most once a minute."""
MAX_SALE_END_LOOKUPS = 25
"""App pages fetched per scrape to learn when new sales end."""


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)


class SteamSales(GroupCog, name="steam", description="Get notified about free and discounted Steam games"):
    """Lists Steam sales on request and DMs subscribers new ones, re-checking sales right after they end."""

    _task: asyncio.Task[None] | None = None

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
        """Scrape every ``update_interval`` and re-check sales just after they end, forever."""
        next_scrape = utc_now()
        while True:
            now = utc_now()
            if now >= next_scrape:
                await self._guarded(self.scrape(now))
                next_scrape = now + timedelta(seconds=SteamSettings.update_interval)
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
        """Scrape Steam's specials, store them, look up when new sales end, and DM subscribers new sales.

        Scrapes down to the lowest subscriber threshold, so every subscriber's sales are found.
        """
        with Session(self._bind) as session:
            store = SteamSaleStore(session)
            lowest = store.lowest_threshold()
            percent = DEFAULT_THRESHOLD if lowest is None else lowest
            without_end: list[SteamSale] = []
            async with SteamScraper() as scraper:
                async for scraped in scraper.get_sales_from_search(SteamSettings.search_url, percent):
                    sale, is_new = store.record(scraped, now=now, outdated_after=self._outdated_after)
                    if is_new and sale.sale_end is None and sale.steam_url.is_app:
                        without_end.append(sale)
                for sale in without_end[:MAX_SALE_END_LOOKUPS]:
                    details = await scraper.get_game_sale(sale.steam_url, now)
                    if isinstance(details, ScrapedSale):
                        store.update_from_app_page(sale, details, now=now)
            notified = await SteamSaleNotifier(self.bot.client, store, color=SteamSettings.embed_color).notify(
                now=now,
                content=self._notification_content(),
            )
            self.logger.info(t"Steam scrape done (threshold {percent} percent), notified {notified} subscriber(s)")

    async def recheck_due(self, now: datetime) -> None:
        """Check the sales whose announced end has passed: update those still running, remove those that ended."""
        with Session(self._bind) as session:
            store = SteamSaleStore(session)
            due = store.due_rechecks(now=now, delay=self._recheck_delay)
            if not due:
                return
            async with SteamScraper() as scraper:
                for sale in due:
                    details = await scraper.get_game_sale(sale.steam_url, now) if sale.steam_url.is_app else None
                    match details:
                        case ScrapeFailure():
                            self.logger.warning(t"Could not re-check {sale.url}; trying again later")
                        case ScrapedSale():
                            store.update_from_app_page(sale, details, now=now)
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
