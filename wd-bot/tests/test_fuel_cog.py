"""Unit tests: the /fuel commands, and the efficiency graph sent as a file (no network)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING

from sqlmodel import Session, select
from wd_bot.registry import CommandRegistry
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
    cog = Fuel.__new__(Fuel)
    cog.bot = SimpleNamespace(registry=CommandRegistry())  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    return cog


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
        (refuel,) = session.exec(select(CarFuels)).all()
    assert (refuel.user_id, refuel.price, refuel.distance, refuel.amount) == (ASKER_ID, 72.5, 600.0, 40.0)
    assert "15.00 distance per unit" in discord_client.interaction_responses()[0]["data"]["content"]


async def test_add_refuses_non_positive_values(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await Fuel.add.invoke(_cog(engine), make_interaction("fuel"), _numbers(price=72.5, distance=600, amount=0))

    with Session(engine) as session:
        assert session.exec(select(CarFuels)).all() == []
    assert "more than 0" in discord_client.interaction_responses()[0]["data"]["content"]


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
