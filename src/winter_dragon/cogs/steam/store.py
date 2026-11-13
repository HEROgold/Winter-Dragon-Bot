"""Storing and querying Steam sales and their subscribers."""

lazy from typing import TYPE_CHECKING

lazy from sqlmodel import col, or_
lazy from wd_db.extension._herogold import Repository, Scoped

lazy from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties, SteamUsers


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Sequence
    lazy from datetime import datetime, timedelta

    lazy from sqlmodel import Session
    lazy from wd_discord.snowflake import Snowflake

    lazy from winter_dragon.cogs.steam.scrapers import ScrapedSale


class SteamSaleStore(Repository[SteamSale], Scoped):
    """Reads and writes Steam sales through one database session; the caller commits."""

    def __init__(self, session: Session) -> None:
        """Use ``session`` for every read and write."""
        super().__init__(session)
        self._properties = Repository[SteamSaleProperties](session)
        self._users = Repository[SteamUsers](session)

    def record(self, scraped: ScrapedSale, *, now: datetime, outdated_after: timedelta) -> tuple[SteamSale, bool]:
        """Store one scraped sale; see :meth:`record_many`."""
        return self.record_many([scraped], now=now, outdated_after=outdated_after)[0]

    def record_many(
        self,
        scraped: Iterable[ScrapedSale],
        *,
        now: datetime,
        outdated_after: timedelta,
    ) -> list[tuple[SteamSale, bool]]:
        """Store scraped sales, returning each stored row with whether it counts as new.

        A sale is new when it wasn't known, was deleted (it's restored), or was outdated (not seen for
        ``outdated_after``) and so worth announcing again. A known sale keeps its ``sale_end`` unless the scrape
        found one. The known sales and their properties are loaded in one query each, whatever the batch size.
        """
        batch = list(scraped)
        by_id: dict[int | None, ScrapedSale] = {sale.id: sale for sale in batch}
        outdated: set[int | None] = set()

        def update(stored: SteamSale, _: SteamSale) -> None:
            if stored.is_outdated(outdated_after, now):
                outdated.add(stored.id)
            self._update(stored, by_id[stored.id], now)

        fresh = [
            SteamSale(
                id=sale.id,
                title=sale.title,
                url=sale.url,
                sale_percent=sale.sale_percent,
                final_price=sale.final_price,
                update_datetime=now,
                discovered_at=now,
                sale_end=sale.sale_end,
            )
            for sale in batch
        ]
        recorded: list[tuple[SteamSale, bool]] = []
        for result in self.upsert(fresh, update):
            is_new = result.created or result.restored or result.row.id in outdated
            if is_new and not result.created:
                result.row.discovered_at = now
            recorded.append((result.row, is_new))
        self._add_properties(batch)
        self.session.flush()
        return recorded

    @staticmethod
    def _update(row: SteamSale, sale: ScrapedSale, now: datetime) -> None:
        row.title = sale.title
        row.url = sale.url
        row.sale_percent = sale.sale_percent
        row.final_price = sale.final_price
        row.update_datetime = now
        if sale.sale_end is not None:
            row.sale_end = sale.sale_end

    def refresh(self, rechecked: Iterable[tuple[SteamSale, ScrapedSale]], *, now: datetime) -> None:
        """Apply what Steam now says about each sale: its current discount, end and properties.

        An end that has already passed is dropped, so a sale still running past its announced end waits for the next
        regular scrape instead of being checked again in a loop. The properties are looked up once for all of them.
        """
        pairs = list(rechecked)
        for sale, scraped in pairs:
            sale.sale_percent = scraped.sale_percent
            sale.final_price = scraped.final_price
            sale.update_datetime = now
            sale.sale_end = scraped.sale_end if scraped.sale_end is not None and scraped.sale_end > now else None
            self.session.add(sale)
        self._add_properties(scraped for _, scraped in pairs)

    def _add_properties(self, scraped: Iterable[ScrapedSale]) -> None:
        """Store any property the sales don't have yet, restoring the ones they had before, in one lookup."""
        rows = [SteamSaleProperties(steam_sale_id=sale.id, property=kind) for sale in scraped for kind in sale.properties]
        self._properties.upsert(rows)

    def remove(self, sales: Iterable[SteamSale]) -> None:
        """Soft-delete ``sales`` and their properties, in two statements whatever their number."""
        ids = [sale.id for sale in sales if sale.id is not None]
        if not ids:
            return
        self._properties.qs().where(col(SteamSaleProperties.steam_sale_id).in_(ids)).soft_delete()
        self.qs().where(col(SteamSale.id).in_(ids)).soft_delete()

    def properties(self, sales: Iterable[SteamSale]) -> dict[int, set[SaleTypes]]:
        """Return the properties of each of ``sales`` that has any, by sale ID."""
        found = {sale.id: {row.property for row in sale.properties} for sale in sales if sale.id is not None}
        return {sale_id: kinds for sale_id, kinds in found.items() if kinds}

    def current_sales(self, percent: int, *, now: datetime, outdated_after: timedelta) -> list[SteamSale]:
        """Return the sales of at least ``percent`` still running: biggest discount first, then cheapest.

        A sale runs until its known end, or without one, until it's outdated (not seen for ``outdated_after``).
        """
        return (
            self.qs()
            .where(
                col(SteamSale.sale_percent) >= percent,
                or_(col(SteamSale.sale_end) > now, col(SteamSale.update_datetime) > now - outdated_after),
            )
            .order_by(col(SteamSale.sale_percent).desc(), col(SteamSale.final_price))
            .all()
        )

    def unseen_without_end(self, moment: datetime, percent: int, *, outdated_after: timedelta) -> list[SteamSale]:
        """Return the shown sales of at least ``percent`` last seen before ``moment``, longest unseen first.

        Sales with a known end are left out: they're re-checked once they end (see :meth:`due_rechecks`).
        """
        return (
            self.qs()
            .where(
                col(SteamSale.sale_percent) >= percent,
                col(SteamSale.update_datetime) < moment,
                col(SteamSale.update_datetime) > moment - outdated_after,
                col(SteamSale.sale_end).is_(None),
            )
            .order_by(col(SteamSale.update_datetime))
            .all()
        )

    def due_rechecks(self, *, now: datetime, delay: timedelta) -> Sequence[SteamSale]:
        """Return the sales whose announced end was at least ``delay`` ago."""
        return self.qs().where(col(SteamSale.sale_end) <= now - delay).all()

    def next_recheck(self, *, delay: timedelta) -> datetime | None:
        """Return when the next sale is due for a re-check, if any sale has a known end."""
        soonest = self.qs().where(col(SteamSale.sale_end).is_not(None)).order_by(col(SteamSale.sale_end)).first()
        return None if soonest is None or soonest.sale_end is None else soonest.sale_end + delay

    def new_since(self, moment: datetime, percent: int) -> list[SteamSale]:
        """Return the sales of at least ``percent`` discovered after ``moment``, newest first."""
        return (
            self.qs()
            .where(col(SteamSale.sale_percent) >= percent, col(SteamSale.discovered_at) > moment)
            .order_by(col(SteamSale.discovered_at).desc())
            .all()
        )

    def subscriber(self, user_id: Snowflake) -> SteamUsers | None:
        """Return the subscription of ``user_id``, if subscribed."""
        return self._users.qs().filter_by(id=int(user_id)).first()

    def subscribers(self) -> Sequence[SteamUsers]:
        """Return every subscribed user."""
        return self._users.qs().all()

    def lowest_threshold(self) -> int | None:
        """Return the lowest ``sale_threshold`` among subscribers, or ``None`` without subscribers."""
        return min((user.sale_threshold for user in self.subscribers()), default=None)
