"""Storing and querying Steam sales and their subscribers."""

from __future__ import annotations

lazy from collections import defaultdict
lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlmodel import col, or_, select
lazy from wd_db.extension.lifecycle import alive, create_or_restore, soft_delete

lazy from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties, SteamUsers


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Sequence
    lazy from datetime import datetime, timedelta

    lazy from sqlmodel import Session

    lazy from winter_dragon.cogs.steam.scrapers import ScrapedSale


@dataclass
class SteamSaleStore:
    """Reads and writes Steam sales through one database session."""

    session: Session

    def record(self, scraped: ScrapedSale, *, now: datetime, outdated_after: timedelta) -> tuple[SteamSale, bool]:
        """Store a scraped sale, returning the stored row and whether it counts as new.

        A sale is new when it wasn't known, was deleted (it's restored), or was outdated (not seen for
        ``outdated_after``) and so worth announcing again. A known sale keeps its ``sale_end`` unless the scrape
        found one.
        """
        sale = self.session.exec(alive(SteamSale).where(SteamSale.id == scraped.id)).first()
        is_new = sale is None or sale.is_outdated(outdated_after, now)
        if sale is None:
            sale = create_or_restore(
                self.session,
                SteamSale(
                    id=scraped.id,
                    title=scraped.title,
                    url=scraped.url,
                    sale_percent=scraped.sale_percent,
                    final_price=scraped.final_price,
                    update_datetime=now,
                    discovered_at=now,
                    sale_end=scraped.sale_end,
                ),
            )
        else:
            sale.title = scraped.title
            sale.url = scraped.url
            sale.sale_percent = scraped.sale_percent
            sale.final_price = scraped.final_price
            sale.update_datetime = now
            if is_new:
                sale.discovered_at = now
            if scraped.sale_end is not None:
                sale.sale_end = scraped.sale_end
        self.session.add(sale)
        self._add_properties(scraped.id, scraped.properties)
        self.session.commit()
        self.session.refresh(sale)
        return sale, is_new

    def refresh(self, sale: SteamSale, scraped: ScrapedSale, *, now: datetime) -> None:
        """Apply what Steam now says about ``sale``: its current discount, end and properties.

        An end that has already passed is dropped, so a sale still running past its announced end waits for the
        next regular scrape instead of being checked again in a loop.
        """
        sale.sale_percent = scraped.sale_percent
        sale.final_price = scraped.final_price
        sale.update_datetime = now
        sale.sale_end = scraped.sale_end if scraped.sale_end is not None and scraped.sale_end > now else None
        self.session.add(sale)
        self._add_properties(sale.id, scraped.properties)
        self.session.commit()

    def _add_properties(self, sale_id: int | None, properties: Iterable[SaleTypes]) -> None:
        """Store any of ``properties`` the sale doesn't have yet, restoring the ones it had before."""
        if sale_id is None:
            return
        known = {row.property for row in self._properties_of(sale_id)}
        for sale_type in set(properties) - known:
            create_or_restore(self.session, SteamSaleProperties(steam_sale_id=sale_id, property=sale_type))

    def _properties_of(self, sale_id: int | None) -> Sequence[SteamSaleProperties]:
        return self.session.exec(alive(SteamSaleProperties).where(SteamSaleProperties.steam_sale_id == sale_id)).all()

    def remove(self, sale: SteamSale) -> None:
        """Soft-delete ``sale`` and its properties."""
        for row in self._properties_of(sale.id):
            soft_delete(self.session, row)
        soft_delete(self.session, sale)
        self.session.commit()

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

    def subscriber(self, user_id: int) -> SteamUsers | None:
        """Return the subscription of ``user_id``, if subscribed."""
        return self.session.exec(alive(SteamUsers).where(SteamUsers.id == user_id)).first()

    def subscribers(self) -> Sequence[SteamUsers]:
        """Return every subscribed user."""
        return self.session.exec(alive(SteamUsers)).all()

    def lowest_threshold(self) -> int | None:
        """Return the lowest ``sale_threshold`` among subscribers, or ``None`` without subscribers."""
        thresholds = [user.sale_threshold for user in self.subscribers()]
        return min(thresholds, default=None)
