"""Unit tests: the /steam commands, page buttons, the scrape, and the re-check after a sale ends (no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, ClassVar, Self
from unittest.mock import AsyncMock

import pytest
from sqlmodel import Session, select
from wd_bot.auto_sync import CommandRecord, GlobalSyncedCommand
from wd_config.steam import SteamSettings
from wd_discord.gateway.events import InteractionDataOption, Message
from wd_discord.resources.channel import Channel

import winter_dragon.cogs.steam.cog as module
from winter_dragon.cogs.steam.cog import SteamSales
from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamUsers
from winter_dragon.cogs.steam.scrapers import ScrapedSale, ScrapeFailure
from winter_dragon.cogs.steam.store import SteamSaleStore
from winter_dragon.cogs.steam.urls import SteamURL, StoreItemID


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterable

    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
OUTDATED = timedelta(hours=30)
ASKER_ID = 3


def app_sale(sale_id: int, *, percent: int = 100, sale_end: datetime | None = None) -> ScrapedSale:
    """Build a scraped app sale."""
    return ScrapedSale(
        id=sale_id,
        title=f"Game {sale_id}",
        url=SteamURL(f"https://store.steampowered.com/app/{sale_id}/"),
        sale_percent=percent,
        final_price=0.0,
        sale_end=sale_end,
    )


class FakeScraper:
    """Serves canned query results and current sales instead of Steam."""

    sales: ClassVar[list[ScrapedSale]] = []
    current: ClassVar[dict[str, ScrapedSale | ScrapeFailure | None]] = {}
    """What Steam says about each store page's item now; ``None`` (not on sale) when missing."""
    queries: ClassVar[list[tuple[int, int | None]]] = []

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        """Accept and ignore the real scraper's HTTP client, throttle and country."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def query_sales(self, percent: int, limit: int | None = None) -> AsyncGenerator[ScrapedSale]:
        """Yield the canned sales of at least ``percent``, remembering the query."""
        FakeScraper.queries.append((percent, limit))
        for sale in self.sales:
            if sale.sale_percent >= percent:
                yield sale

    async def get_sales(
        self,
        items: Iterable[StoreItemID],
    ) -> AsyncGenerator[tuple[StoreItemID, ScrapedSale | ScrapeFailure | None]]:
        """Yield the canned current sale of each item."""
        for item in items:
            yield item, self.current.get(item.url)


@pytest.fixture(autouse=True)
def fake_steam(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeScraper.sales = []
    FakeScraper.current = {}
    FakeScraper.queries = []
    monkeypatch.setattr(module, "SteamScraper", FakeScraper)
    monkeypatch.setattr(module, "utc_now", lambda: NOW)


def _cog(engine: Engine) -> tuple[SteamSales, SimpleNamespace]:
    """Build a SteamSales cog on ``engine`` without running Cog.__init__, with a mocked client."""
    message = Message.model_validate(
        {
            "id": "5",
            "channel_id": "6",
            "author": {"id": "2", "username": "bot", "discriminator": "0"},
            "content": "",
            "timestamp": "2026-10-08T12:00:00+00:00",
            "tts": False,
            "mention_everyone": False,
        },
    )
    client = SimpleNamespace(
        create_interaction_response=AsyncMock(),
        defer_interaction=AsyncMock(),
        edit_original_interaction_response=AsyncMock(),
        update_interaction_message=AsyncMock(),
        create_dm=AsyncMock(return_value=Channel.model_validate({"id": "6", "type": 1})),
        create_message=AsyncMock(return_value=message),
    )
    cog = SteamSales.__new__(SteamSales)
    cog.bot = SimpleNamespace(client=client)  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    return cog, client


def _seed(engine: Engine, *sales: ScrapedSale, now: datetime = NOW) -> None:
    with Session(engine) as session:
        for sale in sales:
            SteamSaleStore(session).record(sale, now=now, outdated_after=OUTDATED)


def _percent(value: int) -> list[InteractionDataOption]:
    return [InteractionDataOption(name="percent", type=4, value=value)]


def _sync_steam_group(engine: Engine, discord_command_id: str = "42") -> None:
    """Record the /steam group as synced, so mentions of it become clickable."""
    with Session(engine) as session:
        record = CommandRecord(name="steam")
        session.add(record)
        session.commit()
        session.refresh(record)
        assert record.id is not None
        session.add(GlobalSyncedCommand(command_id=record.id, signature="s", discord_command_id=discord_command_id))
        session.commit()


async def test_add_subscribes_once(engine: Engine, make_interaction: InteractionFactory) -> None:
    _sync_steam_group(engine)
    cog, client = _cog(engine)

    await SteamSales.add.invoke(cog, make_interaction("steam"), [])
    await SteamSales.add.invoke(cog, make_interaction("steam"), [])

    with Session(engine) as session:
        (user,) = session.exec(select(SteamUsers)).all()
    assert user.id == ASKER_ID
    assert user.sale_threshold == module.DEFAULT_THRESHOLD
    first, second = client.create_interaction_response.await_args_list
    assert "</steam show:42>" in first.kwargs["content"]
    assert second.kwargs["content"] == "Already in the list of recipients"


async def test_percentage_updates_the_threshold(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog, client = _cog(engine)
    await SteamSales.add.invoke(cog, make_interaction("steam"), [])

    await SteamSales.percentage.invoke(cog, make_interaction("steam"), _percent(75))

    with Session(engine) as session:
        assert session.exec(select(SteamUsers)).one().sale_threshold == 75
    assert client.create_interaction_response.await_args.kwargs["content"] == "Changed your sale notification threshold to 75%."


async def test_percentage_rejects_values_outside_0_to_100(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog, client = _cog(engine)
    await SteamSales.percentage.invoke(cog, make_interaction("steam"), _percent(150))
    assert "between 0 and 100" in client.create_interaction_response.await_args.kwargs["content"]


async def test_remove_unsubscribes(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog, client = _cog(engine)
    await SteamSales.add.invoke(cog, make_interaction("steam"), [])

    await SteamSales.remove.invoke(cog, make_interaction("steam"), [])

    with Session(engine) as session:
        assert session.exec(select(SteamUsers)).all() == []
    assert client.create_interaction_response.await_args.kwargs["content"] == "I will no longer notify you of new steam games."


async def test_show_without_sales_replies_ephemerally(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog, client = _cog(engine)

    await SteamSales.show.invoke(cog, make_interaction("steam"), _percent(90))

    client.create_interaction_response.assert_awaited_once()
    assert client.create_interaction_response.await_args.kwargs["ephemeral"] is True
    client.defer_interaction.assert_not_awaited()


async def test_show_defers_then_edits_in_the_first_page(engine: Engine, make_interaction: InteractionFactory) -> None:
    _seed(engine, *(app_sale(index) for index in range(1, 8)))
    cog, client = _cog(engine)
    interaction = make_interaction("steam")

    await SteamSales.show.invoke(cog, interaction, _percent(90))

    client.defer_interaction.assert_awaited_once_with(interaction)
    kwargs = client.edit_original_interaction_response.await_args.kwargs
    (embed,) = kwargs["embeds"]
    assert embed.footer.text == "Page 1/2 • 7 games total"
    (row,) = kwargs["components"]
    assert row.components[2].custom_id == f"steam-show:{ASKER_ID}:90:1"


async def test_page_button_turns_the_page(engine: Engine, make_component_interaction: ComponentInteractionFactory) -> None:
    _seed(engine, *(app_sale(index) for index in range(1, 8)))
    cog, client = _cog(engine)
    interaction = make_component_interaction(f"steam-show:{ASKER_ID}:90:1")

    await SteamSales.show_page.invoke(cog, interaction, [str(ASKER_ID), "90", "1"])

    kwargs = client.update_interaction_message.await_args.kwargs
    assert kwargs["embeds"][0].footer.text == "Page 2/2 • 7 games total"
    assert kwargs["components"][0].components[2].disabled  # last page


async def test_page_button_only_works_for_the_invoker(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
) -> None:
    _seed(engine, app_sale(1))
    cog, client = _cog(engine)

    await SteamSales.show_page.invoke(cog, make_component_interaction("steam-show:999:90:1"), ["999", "90", "1"])

    client.update_interaction_message.assert_not_awaited()
    assert client.create_interaction_response.await_args.kwargs["ephemeral"] is True


async def test_scrape_stores_sales_with_their_end_and_notifies(engine: Engine) -> None:
    end = NOW + timedelta(days=3)
    FakeScraper.sales = [app_sale(1, sale_end=end)]
    with Session(engine) as session:
        session.add(SteamUsers(id=7, sale_threshold=30, last_notification=NOW - timedelta(hours=1)))
        session.commit()
    _sync_steam_group(engine)
    cog, client = _cog(engine)

    await cog.scrape(NOW)

    # every sale from complete_percent up, then the top sellers down to the lowest subscriber threshold
    assert FakeScraper.queries == [(SteamSettings.complete_percent, None), (30, SteamSettings.top_sellers)]
    with Session(engine) as session:
        sale = session.exec(select(SteamSale)).one()  # listed by both queries, stored once
        assert sale.sale_end == end
        assert session.exec(select(SteamUsers)).one().last_notification == NOW
    client.create_dm.assert_awaited_once_with(7)


async def test_scrape_without_subscribers_stores_down_to_the_configured_percent(engine: Engine) -> None:
    _sync_steam_group(engine)
    cog, _client = _cog(engine)
    await cog.scrape(NOW)
    assert FakeScraper.queries[-1] == (SteamSettings.stored_percent, SteamSettings.top_sellers)


async def test_scrape_ignores_subscriber_thresholds_above_the_configured_percent(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(SteamUsers(id=7, sale_threshold=100, last_notification=NOW))
        session.commit()
    _sync_steam_group(engine)
    cog, _client = _cog(engine)
    await cog.scrape(NOW)
    assert FakeScraper.queries[-1] == (SteamSettings.stored_percent, SteamSettings.top_sellers)


@pytest.mark.parametrize(
    ("percent", "expected"),
    [
        (50, [(90, None), (50, 2000)]),
        (90, [(90, None)]),  # nothing below the complete range to take top sellers from
        (95, [(95, None)]),
    ],
)
def test_sale_queries(percent: int, expected: list[tuple[int, int | None]]) -> None:
    assert list(module.sale_queries(percent, 90, 2000)) == expected


async def test_recheck_removes_ended_sales(engine: Engine) -> None:
    _seed(engine, app_sale(1, sale_end=NOW - timedelta(minutes=5)))
    FakeScraper.current = {"https://store.steampowered.com/app/1/": None}
    cog, _client = _cog(engine)

    await cog.recheck_due(NOW)

    with Session(engine) as session:
        assert session.exec(select(SteamSale)).all() == []


async def test_recheck_updates_sales_that_continue(engine: Engine) -> None:
    _seed(engine, app_sale(1, sale_end=NOW - timedelta(minutes=5)))
    new_end = NOW + timedelta(days=7)
    FakeScraper.current = {"https://store.steampowered.com/app/1/": app_sale(1, percent=75, sale_end=new_end)}
    cog, _client = _cog(engine)

    await cog.recheck_due(NOW)

    with Session(engine) as session:
        sale = session.exec(select(SteamSale)).one()
    assert (sale.sale_percent, sale.sale_end) == (75, new_end)


async def test_recheck_keeps_sales_when_steam_is_unavailable(engine: Engine) -> None:
    ended = NOW - timedelta(minutes=5)
    _seed(engine, app_sale(1, sale_end=ended))
    FakeScraper.current = {"https://store.steampowered.com/app/1/": ScrapeFailure.UNAVAILABLE}
    cog, _client = _cog(engine)

    await cog.recheck_due(NOW)

    with Session(engine) as session:
        assert session.exec(select(SteamSale)).one().sale_end == ended


async def test_recheck_ignores_sales_not_yet_due(engine: Engine) -> None:
    _seed(engine, app_sale(1, sale_end=NOW + timedelta(hours=1)))
    FakeScraper.current = {"https://store.steampowered.com/app/1/": None}
    cog, _client = _cog(engine)

    await cog.recheck_due(NOW)

    with Session(engine) as session:
        assert len(session.exec(select(SteamSale)).all()) == 1


def test_dlc_property_is_kept_on_refresh(engine: Engine) -> None:
    _seed(engine, app_sale(1))
    with Session(engine) as session:
        store = SteamSaleStore(session)
        sale = session.exec(select(SteamSale)).one()
        dlc = ScrapedSale(
            id=1,
            title="Game 1",
            url=sale.steam_url,
            sale_percent=100,
            final_price=0.0,
            properties=frozenset({SaleTypes.DLC}),
        )
        store.refresh(sale, dlc, now=NOW)
        assert store.properties([sale]) == {1: {SaleTypes.DLC}}


async def test_scrape_verifies_sales_it_no_longer_lists(engine: Engine) -> None:
    earlier = NOW - timedelta(hours=3)
    _seed(engine, app_sale(1), app_sale(2), app_sale(3), now=earlier)
    FakeScraper.sales = [app_sale(1)]
    FakeScraper.current = {
        "https://store.steampowered.com/app/1/": app_sale(1),
        "https://store.steampowered.com/app/2/": None,  # ended
        "https://store.steampowered.com/app/3/": app_sale(3, percent=80),  # no longer a top seller
    }
    _sync_steam_group(engine)
    cog, _client = _cog(engine)

    await cog.scrape(NOW)

    with Session(engine) as session:
        sales = {sale.id: sale for sale in session.exec(select(SteamSale))}
    assert sorted(sales) == [1, 3]
    assert (sales[3].sale_percent, sales[3].update_datetime) == (80, NOW)


async def test_empty_scrape_removes_nothing(engine: Engine) -> None:
    _seed(engine, app_sale(1), now=NOW - timedelta(hours=3))
    FakeScraper.current = {"https://store.steampowered.com/app/1/": None}
    _sync_steam_group(engine)
    cog, _client = _cog(engine)

    await cog.scrape(NOW)

    with Session(engine) as session:
        assert len(session.exec(select(SteamSale)).all()) == 1


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 10, 8, 12, 0, tzinfo=UTC), datetime(2026, 10, 8, 15, 0, tzinfo=UTC)),  # interval first
        (datetime(2026, 10, 8, 15, 0, tzinfo=UTC), datetime(2026, 10, 8, 17, 5, tzinfo=UTC)),  # rollover first
        (datetime(2026, 10, 8, 17, 5, tzinfo=UTC), datetime(2026, 10, 8, 20, 5, tzinfo=UTC)),  # just scraped it
        (datetime(2026, 10, 8, 23, 0, tzinfo=UTC), datetime(2026, 10, 9, 2, 0, tzinfo=UTC)),
    ],
)
def test_next_scrape_time(now: datetime, expected: datetime) -> None:
    assert module.next_scrape_time(now, timedelta(hours=3)) == expected


async def test_scrape_defers_unseen_sales_with_a_known_end(engine: Engine) -> None:
    end = NOW + timedelta(days=2)
    _seed(engine, app_sale(1), app_sale(2, sale_end=end), now=NOW - timedelta(hours=3))
    FakeScraper.sales = [app_sale(1)]
    FakeScraper.current = {"https://store.steampowered.com/app/2/": None}  # would remove it if looked at
    _sync_steam_group(engine)
    cog, _client = _cog(engine)

    await cog.scrape(NOW)

    with Session(engine) as session:
        assert session.exec(select(SteamSale).where(SteamSale.id == 2)).one().sale_end == end


async def test_recheck_waits_while_steam_rate_limits_us(engine: Engine) -> None:
    _seed(engine, app_sale(1, sale_end=NOW - timedelta(minutes=5)))
    FakeScraper.current = {"https://store.steampowered.com/app/1/": None}
    cog, _client = _cog(engine)
    cog.throttle.rate_limited(60)

    await cog.recheck_due(NOW)

    with Session(engine) as session:
        assert len(session.exec(select(SteamSale)).all()) == 1
