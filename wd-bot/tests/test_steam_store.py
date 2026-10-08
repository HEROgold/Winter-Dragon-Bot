"""Unit tests: storing Steam sales, deciding which are new, and the queries the cog runs (sqlite)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, select

from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties, SteamUsers
from winter_dragon.cogs.steam.scrapers import ScrapedSale
from winter_dragon.cogs.steam.store import SteamSaleStore
from winter_dragon.cogs.steam.urls import SteamURL


if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
OUTDATED = timedelta(hours=30)
DELAY = timedelta(minutes=1)


def scraped(
    sale_id: int = 10,
    *,
    percent: int = 100,
    final_price: float = 0.0,
    properties: frozenset[SaleTypes] = frozenset(),
    sale_end: datetime | None = None,
) -> ScrapedSale:
    """Build a scraped app sale."""
    return ScrapedSale(
        id=sale_id,
        title=f"Game {sale_id}",
        url=SteamURL(f"https://store.steampowered.com/app/{sale_id}/"),
        sale_percent=percent,
        final_price=final_price,
        properties=properties,
        sale_end=sale_end,
    )


@pytest.fixture
def store(engine: Engine) -> Generator[SteamSaleStore]:
    with Session(engine) as session:
        yield SteamSaleStore(session)


def test_first_sighting_is_new(store: SteamSaleStore) -> None:
    sale, is_new = store.record(scraped(), now=NOW, outdated_after=OUTDATED)
    assert is_new
    assert sale.discovered_at == NOW
    assert sale.update_datetime == NOW


def test_seeing_a_known_sale_again_is_not_new(store: SteamSaleStore) -> None:
    store.record(scraped(), now=NOW, outdated_after=OUTDATED)
    later = NOW + timedelta(hours=3)
    sale, is_new = store.record(scraped(percent=90), now=later, outdated_after=OUTDATED)
    assert not is_new
    assert sale.discovered_at == NOW
    assert sale.update_datetime == later
    assert sale.sale_percent == 90


def test_an_outdated_sale_seen_again_is_new_again(store: SteamSaleStore) -> None:
    store.record(scraped(), now=NOW, outdated_after=OUTDATED)
    much_later = NOW + OUTDATED + timedelta(hours=1)
    sale, is_new = store.record(scraped(), now=much_later, outdated_after=OUTDATED)
    assert is_new
    assert sale.discovered_at == much_later


def test_a_known_end_survives_a_scrape_without_one(store: SteamSaleStore) -> None:
    end = NOW + timedelta(days=2)
    store.record(scraped(sale_end=end), now=NOW, outdated_after=OUTDATED)
    sale, _ = store.record(scraped(), now=NOW + timedelta(hours=3), outdated_after=OUTDATED)
    assert sale.sale_end == end


def test_properties_are_stored_once(store: SteamSaleStore) -> None:
    sale, _ = store.record(scraped(properties=frozenset({SaleTypes.DLC})), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(properties=frozenset({SaleTypes.DLC})), now=NOW, outdated_after=OUTDATED)
    rows = store.session.exec(select(SteamSaleProperties)).all()
    assert [row.property for row in rows] == [SaleTypes.DLC]
    assert store.properties([sale]) == {10: {SaleTypes.DLC}}


def test_current_sales_hide_outdated_and_cheap_ones(store: SteamSaleStore) -> None:
    store.record(scraped(1, percent=100, final_price=0.0), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(2, percent=100, final_price=1.0), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(3, percent=95), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(4, percent=50), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(5, percent=100), now=NOW - OUTDATED, outdated_after=OUTDATED)

    sales = store.current_sales(90, now=NOW, outdated_after=OUTDATED)

    assert [sale.id for sale in sales] == [1, 2, 3]  # biggest discount first, then cheapest


def test_rechecks_are_due_a_delay_after_the_end(store: SteamSaleStore) -> None:
    store.record(scraped(1, sale_end=NOW), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(2, sale_end=NOW + timedelta(hours=1)), now=NOW, outdated_after=OUTDATED)
    store.record(scraped(3), now=NOW, outdated_after=OUTDATED)

    assert store.due_rechecks(now=NOW, delay=DELAY) == []
    assert [sale.id for sale in store.due_rechecks(now=NOW + DELAY, delay=DELAY)] == [1]
    assert store.next_recheck(delay=DELAY) == NOW + DELAY


def test_no_recheck_without_known_ends(store: SteamSaleStore) -> None:
    store.record(scraped(), now=NOW, outdated_after=OUTDATED)
    assert store.next_recheck(delay=DELAY) is None


def test_refresh_drops_an_end_that_already_passed(store: SteamSaleStore) -> None:
    sale, _ = store.record(scraped(sale_end=NOW), now=NOW, outdated_after=OUTDATED)
    store.refresh(sale, scraped(percent=80, sale_end=NOW), now=NOW + DELAY)
    assert sale.sale_end is None
    assert sale.sale_percent == 80

    future = NOW + timedelta(days=1)
    store.refresh(sale, scraped(sale_end=future), now=NOW + DELAY)
    assert sale.sale_end == future


def test_remove_deletes_the_sale_and_its_properties(store: SteamSaleStore) -> None:
    sale, _ = store.record(scraped(properties=frozenset({SaleTypes.DLC})), now=NOW, outdated_after=OUTDATED)
    store.remove(sale)
    assert store.session.exec(select(SteamSale)).all() == []
    assert store.session.exec(select(SteamSaleProperties)).all() == []


def test_new_since_filters_by_discovery_and_threshold(store: SteamSaleStore) -> None:
    store.record(scraped(1, percent=100), now=NOW - timedelta(hours=1), outdated_after=OUTDATED)
    store.record(scraped(2, percent=100), now=NOW + timedelta(hours=1), outdated_after=OUTDATED)
    store.record(scraped(3, percent=40), now=NOW + timedelta(hours=1), outdated_after=OUTDATED)
    assert [sale.id for sale in store.new_since(NOW, 50)] == [2]


def test_lowest_threshold(store: SteamSaleStore) -> None:
    assert store.lowest_threshold() is None
    store.session.add(SteamUsers(id=1, sale_threshold=80, last_notification=NOW))
    store.session.add(SteamUsers(id=2, sale_threshold=0, last_notification=NOW))
    store.session.commit()
    assert store.lowest_threshold() == 0


def test_a_sale_with_a_known_end_stays_current_until_it_ends(store: SteamSaleStore) -> None:
    long_ago = NOW - 2 * OUTDATED
    store.record(scraped(1, sale_end=NOW + timedelta(hours=1)), now=long_ago, outdated_after=OUTDATED)
    store.record(scraped(2, sale_end=NOW - timedelta(hours=1)), now=long_ago, outdated_after=OUTDATED)

    assert [sale.id for sale in store.current_sales(0, now=NOW, outdated_after=OUTDATED)] == [1]


def test_unseen_without_end_skips_sales_with_a_known_end(store: SteamSaleStore) -> None:
    earlier = NOW - timedelta(hours=3)
    store.record(scraped(1), now=earlier, outdated_after=OUTDATED)
    store.record(scraped(2, sale_end=NOW + timedelta(days=1)), now=earlier, outdated_after=OUTDATED)
    store.record(scraped(3), now=NOW, outdated_after=OUTDATED)  # seen this scrape

    unseen = store.unseen_without_end(NOW, 0, outdated_after=OUTDATED)

    assert [sale.id for sale in unseen] == [1]
