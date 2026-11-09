"""Storing and querying Steam sales and their subscribers."""

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections import defaultdict

lazy from sqlmodel import col, or_, select
lazy from wd_db.extension.lifecycle import alive, alive_by_id, soft_delete, upsert

lazy from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties, SteamUsers


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Mapping, Sequence
    lazy from datetime import datetime, timedelta

    lazy from sqlmodel import Session
    lazy from wd_discord.snowflake import Snowflake

    lazy from winter_dragon.cogs.steam.scrapers import ScrapedSale


@dataclass
class SteamSaleStore:
    """Reads and writes Steam sales through one database session; the caller commits."""

    session: Session

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
        found one. The known sales and their properties are loaded in two queries, whatever the batch size.
        """
        batch = list(scraped)
        ids = [sale.id for sale in batch]
        stored = {row.id: row for row in self.session.exec(select(SteamSale).where(col(SteamSale.id).in_(ids)))}
        property_rows = self.property_rows(ids)
        recorded: list[tuple[SteamSale, bool]] = []
        for sale in batch:
            known = stored.get(sale.id)
            if known is not None and known.deleted_at is not None:
                known = None
            is_new = known is None or known.is_outdated(outdated_after, now)

            fresh = SteamSale(
                id=sale.id,
                title=sale.title,
                url=sale.url,
                sale_percent=sale.sale_percent,
                final_price=sale.final_price,
                update_datetime=now,
                discovered_at=now,
                sale_end=sale.sale_end,
            )
            if sale.id in stored:  # loaded above, so upsert finds it in the session without asking the database
                row = upsert(self.session, fresh, lambda row, sale=sale, new=is_new: self._update(row, sale, now, new=new))
            else:
                self.session.add(fresh)
                row = fresh
            self._add_properties(sale.id, sale.properties, property_rows[sale.id])
            recorded.append((row, is_new))
        self.session.flush()
        return recorded

    @staticmethod
    def _update(row: SteamSale, sale: ScrapedSale, now: datetime, *, new: bool) -> None:
        row.title = sale.title
        row.url = sale.url
        row.sale_percent = sale.sale_percent
        row.final_price = sale.final_price
        row.update_datetime = now
        if new:
            row.discovered_at = now
        if sale.sale_end is not None:
            row.sale_end = sale.sale_end

    def refresh(
        self,
        sale: SteamSale,
        scraped: ScrapedSale,
        *,
        now: datetime,
        stored: Mapping[SaleTypes, SteamSaleProperties],
    ) -> None:
        """Apply what Steam now says about ``sale``: its current discount, end and properties.

        ``stored`` holds the sale's property rows, from :meth:`property_rows`. An end that has already passed is
        dropped, so a sale still running past its announced end waits for the next regular scrape instead of being
        checked again in a loop.
        """
        sale.sale_percent = scraped.sale_percent
        sale.final_price = scraped.final_price
        sale.update_datetime = now
        sale.sale_end = scraped.sale_end if scraped.sale_end is not None and scraped.sale_end > now else None
        self.session.add(sale)
        self._add_properties(sale.id, scraped.properties, stored)

    def _add_properties(
        self,
        sale_id: int | None,
        properties: Iterable[SaleTypes],
        stored: Mapping[SaleTypes, SteamSaleProperties],
    ) -> None:
        """Store any of ``properties`` the sale doesn't have yet, restoring the ones it had before."""
        if sale_id is None:
            return
        for sale_type in set(properties):
            row = stored.get(sale_type)
            if row is None:
                self.session.add(SteamSaleProperties(steam_sale_id=sale_id, property=sale_type))
            elif row.deleted_at is not None:
                row.deleted_at = None
                self.session.add(row)

    def property_rows(self, sale_ids: Iterable[int | None]) -> defaultdict[int, dict[SaleTypes, SteamSaleProperties]]:
        """Return the property rows (deleted ones too) of each sale ID, in one query."""
        ids = [sale_id for sale_id in sale_ids if sale_id is not None]
        found: defaultdict[int, dict[SaleTypes, SteamSaleProperties]] = defaultdict(dict)
        for row in self.session.exec(select(SteamSaleProperties).where(col(SteamSaleProperties.steam_sale_id).in_(ids))):
            found[row.steam_sale_id][row.property] = row
        return found

    def remove(self, sale: SteamSale, stored: Mapping[SaleTypes, SteamSaleProperties]) -> None:
        """Soft-delete ``sale`` and its properties, given its property rows from :meth:`property_rows`."""
        for row in stored.values():
            if row.deleted_at is None:
                soft_delete(self.session, row)
        soft_delete(self.session, sale)

    def properties(self, sales: Iterable[SteamSale]) -> dict[int, set[SaleTypes]]:
        """Return the properties of each of ``sales``, by sale ID."""
        ids = [sale.id for sale in sales if sale.id is not None]
        found: defaultdict[int, set[SaleTypes]] = defaultdict(set)
        rows = self.session.exec(alive(SteamSaleProperties).where(col(SteamSaleProperties.steam_sale_id).in_(ids)))
        for row in rows:
            found[row.steam_sale_id].add(row.property)
        return dict(found)

    def current_sales(self, percent: int, *, now: datetime, outdated_after: timedelta) -> list[SteamSale]:
        """Return the sales of at least ``percent`` still running: biggest discount first, then cheapest.

        A sale runs until its known end, or without one, until it's outdated (not seen for ``outdated_after``).
        """
        query = alive(SteamSale).where(
            SteamSale.sale_percent >= percent,
            or_(col(SteamSale.sale_end) > now, col(SteamSale.update_datetime) > now - outdated_after),
        )
        return list(self.session.exec(query.order_by(col(SteamSale.sale_percent).desc(), col(SteamSale.final_price))))

    def unseen_without_end(self, moment: datetime, percent: int, *, outdated_after: timedelta) -> list[SteamSale]:
        """Return the shown sales of at least ``percent`` last seen before ``moment``, longest unseen first.

        Sales with a known end are left out: they're re-checked once they end (see :meth:`due_rechecks`).
        """
        query = alive(SteamSale).where(
            SteamSale.sale_percent >= percent,
            col(SteamSale.update_datetime) < moment,
            col(SteamSale.update_datetime) > moment - outdated_after,
            col(SteamSale.sale_end).is_(None),
        )
        return list(self.session.exec(query.order_by(col(SteamSale.update_datetime))))

    def due_rechecks(self, *, now: datetime, delay: timedelta) -> Sequence[SteamSale]:
        """Return the sales whose announced end was at least ``delay`` ago."""
        return self.session.exec(alive(SteamSale).where(col(SteamSale.sale_end) <= now - delay)).all()

    def next_recheck(self, *, delay: timedelta) -> datetime | None:
        """Return when the next sale is due for a re-check, if any sale has a known end."""
        sale_end = self.session.exec(
            select(SteamSale.sale_end)
            .where(col(SteamSale.sale_end).is_not(None), col(SteamSale.deleted_at).is_(None))
            .order_by(col(SteamSale.sale_end)),
        ).first()
        return None if sale_end is None else sale_end + delay

    def new_since(self, moment: datetime, percent: int) -> list[SteamSale]:
        """Return the sales of at least ``percent`` discovered after ``moment``, newest first."""
        query = alive(SteamSale).where(SteamSale.sale_percent >= percent, col(SteamSale.discovered_at) > moment)
        return list(self.session.exec(query.order_by(col(SteamSale.discovered_at).desc())))

    def subscriber(self, user_id: Snowflake) -> SteamUsers | None:
        """Return the subscription of ``user_id``, if subscribed."""
        return alive_by_id(self.session, SteamUsers, int(user_id))

    def subscribers(self) -> Sequence[SteamUsers]:
        """Return every subscribed user."""
        return self.session.exec(alive(SteamUsers)).all()

    def lowest_threshold(self) -> int | None:
        """Return the lowest ``sale_threshold`` among subscribers, or ``None`` without subscribers."""
        thresholds = [user.sale_threshold for user in self.subscribers()]
        return min(thresholds, default=None)
