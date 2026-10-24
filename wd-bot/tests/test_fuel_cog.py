"""Unit tests: the /fuel commands, and the efficiency graph sent as a file (no network)."""

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import LIFECYCLE_COLUMNS, alive, soft_delete
from wd_discord.gateway.events import InteractionDataOption

from winter_dragon.cogs.fuel import CarFuels, Fuel, render_efficiency_graph


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine
    from wd_discord.testing import RecordingClient


ASKER_ID = 3
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
FOLLOWUP = "/webhooks/2/tok"


def _cog(engine: Engine) -> Fuel:
    return detached_cog(Fuel, engine=engine)


def _numbers(**values: float) -> list[InteractionDataOption]:
    return [InteractionDataOption(name=name, type=10, value=value) for name, value in values.items()]


def _refuel(days_ago: int, distance: float, amount: float, user_id: int = ASKER_ID) -> CarFuels:
    return CarFuels(user_id=user_id, amount=amount, distance=distance, price=50.0, timestamp=NOW - timedelta(days=days_ago))


def test_graph_is_a_png() -> None:
    graph = render_efficiency_graph([_refuel(2, 600, 40), _refuel(1, 650, 40.5), _refuel(0, 0, 0)])
    assert graph.startswith(PNG_SIGNATURE)


async def test_add_stores_the_refuel(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await Fuel.add.invoke(_cog(engine), make_interaction("fuel"), _numbers(price=72.5, distance=600, amount=40))

    with Session(engine) as session:
        (refuel,) = session.exec(alive(CarFuels)).all()
    assert (refuel.user_id, refuel.price, refuel.distance, refuel.amount) == (ASKER_ID, 72.5, 600.0, 40.0)
    assert "15.00 distance per unit" in discord_client.interaction_responses()[0]["data"]["content"]


async def test_add_refuses_non_positive_values(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await Fuel.add.invoke(_cog(engine), make_interaction("fuel"), _numbers(price=72.5, distance=600, amount=0))

    with Session(engine) as session:
        assert session.exec(alive(CarFuels)).all() == []
    assert "more than 0" in discord_client.interaction_responses()[0]["data"]["content"]


async def test_add_backdates_a_refuel_to_the_given_day(
    engine: Engine,
    make_interaction: InteractionFactory,
) -> None:
    options = [*_numbers(price=72.5, distance=600, amount=40), InteractionDataOption(name="date", type=3, value="2026-01-15")]
    await Fuel.add.invoke(_cog(engine), make_interaction("fuel"), options)

    with Session(engine) as session:
        (refuel,) = session.exec(alive(CarFuels)).all()
    assert refuel.timestamp == datetime(2026, 1, 15, tzinfo=UTC)


@pytest.mark.parametrize("day", ["15-01-2026", "yesterday", "9999-01-01"])
async def test_add_refuses_a_bad_or_future_date(
    day: str,
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    options = [*_numbers(price=72.5, distance=600, amount=40), InteractionDataOption(name="date", type=3, value=day)]
    await Fuel.add.invoke(_cog(engine), make_interaction("fuel"), options)

    with Session(engine) as session:
        assert session.exec(alive(CarFuels)).all() == []
    assert "YYYY-MM-DD" in discord_client.interaction_responses()[0]["data"]["content"]


async def test_efficiency_without_refuels_says_so(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        session.add(_refuel(1, 600, 40, user_id=99))
        session.commit()

    await Fuel.efficiency.invoke(_cog(engine), make_interaction("fuel"), [])

    assert "haven't logged a refuel" in discord_client.interaction_responses()[0]["data"]["content"]


async def test_efficiency_sends_the_graph_as_a_file(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        session.add_all([_refuel(2, 600, 40), _refuel(1, 650, 40.5)])
        session.commit()

    await Fuel.efficiency.invoke(_cog(engine), make_interaction("fuel"), [])

    assert discord_client.interaction_responses() == [{"type": 5, "data": {"flags": 64}}]
    (followup,) = discord_client.requests_to("POST", FOLLOWUP)
    assert json.loads(followup.data["payload_json"])["attachments"][0]["filename"] == "fuel_efficiency.png"
    ((field, (filename, data, content_type)),) = followup.files
    assert (field, filename, content_type) == ("files[0]", "fuel_efficiency.png", "image/png")
    assert data.startswith(PNG_SIGNATURE)


async def test_an_old_carfuels_table_gains_the_lifecycle_columns_and_keeps_working(
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE carfuels (id INTEGER PRIMARY KEY, user_id BIGINT, amount FLOAT, distance FLOAT,"
                " price FLOAT, timestamp DATETIME)",
            ),
        )
        connection.execute(text(f"INSERT INTO carfuels VALUES (1, {ASKER_ID}, 40, 600, 50, '2026-10-01 12:00:00')"))
    cog = _cog(engine)

    await cog.load()
    await Fuel.add.invoke(cog, make_interaction("fuel"), _numbers(price=72.5, distance=650, amount=40.5))
    await Fuel.efficiency.invoke(cog, make_interaction("fuel"), [])

    assert "distance per unit" in discord_client.interaction_responses()[0]["data"]["content"]
    ((_, (filename, _, _)),) = discord_client.requests_to("POST", FOLLOWUP)[0].files
    assert filename == "fuel_efficiency.png"
    assert set(LIFECYCLE_COLUMNS) <= {column["name"] for column in inspect(engine).get_columns("carfuels")}


async def test_a_soft_deleted_refuel_is_not_counted(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    with Session(engine) as session:
        refuel = _refuel(1, 600, 40)
        session.add(refuel)
        session.commit()
        soft_delete(session, refuel)
        session.commit()

    await Fuel.efficiency.invoke(_cog(engine), make_interaction("fuel"), [])

    assert "haven't logged a refuel" in discord_client.interaction_responses()[0]["data"]["content"]
