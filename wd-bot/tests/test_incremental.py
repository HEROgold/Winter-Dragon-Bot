"""Unit tests: the Incremental catalogue, the game rules (no Discord), and the /incremental cog (sqlite)."""

import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.dialects import postgresql
from sqlmodel import Session, SQLModel
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive, owned_by
from wd_errors import Refused

from winter_dragon.cogs.incremental import game
from winter_dragon.cogs.incremental.catalogue import CatalogueError, load_catalogue
from winter_dragon.cogs.incremental.cog import Incremental
from winter_dragon.cogs.incremental.models import IncrementalSave, SaveBalance, SaveGenerator
from winter_dragon.cogs.privacy.domain import hide_owned


if TYPE_CHECKING:
    from pathlib import Path

    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine
    from wd_discord.testing import RecordingClient

ASKER_ID = 3
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CATALOGUE = """
[[currencies]]
key = "coins"
name = "Coins"
{extra}
[[generators]]
key = "digger"
name = "Digger"
price = [{{ currency = "coins", amount = 10 }}]
produces = [{{ currency = "{produces}", amount = 1 }}]
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "catalogue.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _coins(view: game.SaveView) -> float:
    return next(holding.amount for holding in view.holdings if holding.currency.key == "coins")


def _digger(view: game.SaveView) -> game.Offer:
    return next(offer for offer in view.offers if offer.generator.key == "digger")


def test_shipped_catalogue_loads() -> None:
    catalogue = load_catalogue()
    assert catalogue.currency("coins") is not None
    assert catalogue.generator("digger") is not None


def test_catalogue_values_are_frozen() -> None:
    with pytest.raises(ValidationError):
        load_catalogue().currencies[0].name = "x"


def test_valid_catalogue_parses(tmp_path: Path) -> None:
    catalogue = load_catalogue(_write(tmp_path, CATALOGUE.format(extra="", produces="coins")))
    (digger,) = catalogue.generators
    assert digger.key == "digger"
    assert [(cost.currency, cost.amount) for cost in digger.price_for(0)] == [("coins", 10)]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (CATALOGUE.format(extra="", produces="gold"), "unknown currency"),
        (CATALOGUE.format(extra="", produces="coins") + '\n[[currencies]]\nkey = "coins"\nname = "Again"\n', "unique"),
        (CATALOGUE.format(extra="mystery = 1", produces="coins"), "mystery"),
        ("[[currencies]\n", "can't be read"),
    ],
)
def test_invalid_catalogue_is_a_clear_error(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(CatalogueError, match=message):
        load_catalogue(_write(tmp_path, text))


def test_missing_catalogue_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(CatalogueError, match="can't be read"):
        load_catalogue(tmp_path / "nope.toml")


def test_price_grows_with_owned_count() -> None:
    digger = load_catalogue().generator("digger")
    assert digger is not None
    first, third = next(digger.price_for(0)), next(digger.price_for(2))
    assert third.amount == pytest.approx(first.amount * digger.price_growth**2)


def test_first_open_creates_the_save_with_starting_amounts(engine: Engine) -> None:
    with Session(engine) as session:
        view = game.open_save(session, ASKER_ID, now=NOW)
        again = game.open_save(session, ASKER_ID, now=NOW)

    assert _coins(view) == 10
    assert _coins(again) == 10
    with Session(engine) as session:
        (save,) = session.exec(alive(IncrementalSave)).all()
    assert (save.id, save.settled_at) == (ASKER_ID, NOW)


def test_amounts_include_production_while_away_without_limit(engine: Engine) -> None:
    with Session(engine) as session:
        game.open_save(session, ASKER_ID, now=NOW)
        session.add(SaveGenerator(save_id=ASKER_ID, generator="digger", owned=2))
        session.commit()
        week = game.open_save(session, ASKER_ID, now=NOW + timedelta(days=7))
        year = game.open_save(session, ASKER_ID, now=NOW + timedelta(days=365))

    per_second = 2 * 0.5
    assert _coins(week) == pytest.approx(10 + per_second * 7 * 86400)
    assert _coins(year) == pytest.approx(10 + per_second * 365 * 86400)


def test_save_belongs_to_the_member_and_is_deletable(engine: Engine) -> None:
    with Session(engine) as session:
        game.open_save(session, ASKER_ID, now=NOW)
        game.open_save(session, 4, now=NOW)
        assert [save.id for save in session.exec(owned_by(IncrementalSave, member=ASKER_ID))] == [ASKER_ID]
        game.buy(session, ASKER_ID, "digger", now=NOW)
        assert len(session.exec(owned_by(SaveGenerator, member=ASKER_ID)).all()) == 1
        assert session.exec(owned_by(SaveGenerator, member=4)).all() == []

        hide_owned(session, (SaveGenerator, SaveBalance, IncrementalSave), NOW, member=ASKER_ID)
        session.commit()
        assert session.exec(owned_by(IncrementalSave, member=ASKER_ID)).all() == []
        fresh = game.open_save(session, ASKER_ID, now=NOW)

    assert _coins(fresh) == 10  # a deleted save starts over
    assert _digger(fresh).owned == 0


def test_buy_spends_adds_and_settles_production(engine: Engine) -> None:
    with Session(engine) as session:
        game.open_save(session, ASKER_ID, now=NOW)
        first = game.buy(session, ASKER_ID, "digger", now=NOW)
        second = game.buy(session, ASKER_ID, "digger", now=NOW + timedelta(seconds=1000))

    assert _coins(first) == 0
    assert _digger(first).owned == 1
    assert _digger(second).owned == 2
    assert _coins(second) == pytest.approx(0.5 * 1000 - 10 * 1.15)


def test_buy_without_enough_is_refused_and_changes_nothing(engine: Engine) -> None:
    with Session(engine) as session:
        game.buy(session, ASKER_ID, "digger", now=NOW)
        with pytest.raises(Refused, match="You need .* Coins"):
            game.buy(session, ASKER_ID, "digger", now=NOW)
        view = game.open_save(session, ASKER_ID, now=NOW)

    assert _digger(view).owned == 1
    assert _coins(view) == 0
    assert not _digger(view).affordable


def test_buy_unknown_generator_is_refused(engine: Engine) -> None:
    with Session(engine) as session, pytest.raises(Refused, match="doesn't exist"):
        game.buy(session, ASKER_ID, "nonsense", now=NOW)


def test_buy_locks_the_save_row(engine: Engine) -> None:
    statements: list[str] = []

    def record(state: object) -> None:
        statements.append(str(state.statement.compile(dialect=postgresql.dialect())))

    event.listen(Session, "do_orm_execute", record)
    try:
        with Session(engine) as session:
            game.buy(session, ASKER_ID, "digger", now=NOW)
    finally:
        event.remove(Session, "do_orm_execute", record)

    assert any("FROM incrementalsave" in sql and sql.rstrip().endswith("FOR UPDATE") for sql in statements)


def test_simultaneous_buys_cannot_spend_the_same_coins_twice(tmp_path: Path) -> None:
    """Eight buys race for a save that can pay for one; each transaction takes a write lock when it begins.

    sqlite has no row locks, so ``BEGIN IMMEDIATE`` stands in for PostgreSQL's ``FOR UPDATE`` (asserted in
    :func:`test_buy_locks_the_save_row`). Overspending needs a buy that checks the price in one transaction and
    spends in another, or outside any, and this fails for such a buy.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}", connect_args={"timeout": 30, "check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _manual_transactions(connection: object, _record: object) -> None:
        connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin_immediate(connection: object) -> None:
        connection.exec_driver_sql("BEGIN IMMEDIATE")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        game.open_save(session, ASKER_ID, now=NOW)
    outcomes: list[str] = []
    barrier = threading.Barrier(8)

    def attempt() -> None:
        barrier.wait()
        with Session(engine) as session:
            try:
                game.buy(session, ASKER_ID, "digger", now=NOW)
            except Refused:
                outcomes.append("refused")
            else:
                outcomes.append("bought")

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["bought"] + ["refused"] * 7
    with Session(engine) as session:
        (owned,) = session.exec(alive(SaveGenerator)).all()
        balances = {row.currency: row.amount for row in session.exec(alive(SaveBalance)).all()}
    assert owned.owned == 1
    assert balances["coins"] == 0


def _cog(engine: Engine) -> Incremental:
    return detached_cog(Incremental, engine=engine)


async def test_command_shows_the_save_as_one_embed_with_buttons(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    await Incremental.incremental.invoke(_cog(engine), make_interaction("incremental"), [])

    (response,) = discord_client.interaction_responses()
    (embed,) = response["data"]["embeds"]
    assert "Coins: 10.0" in embed["description"]
    buttons = [button for row in response["data"]["components"] for button in row["components"]]
    assert buttons[0]["custom_id"] == f"incremental-refresh:{ASKER_ID}"
    digger = next(button for button in buttons if button["custom_id"] == f"incremental-buy:{ASKER_ID}:digger")
    assert not digger.get("disabled")
    gem_cutter = next(button for button in buttons if button["custom_id"].endswith(":gem_cutter"))
    assert gem_cutter["disabled"]
    assert any("(can't afford)" in field["value"] for field in embed["fields"])


async def test_refresh_edits_the_same_message(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = make_component_interaction(f"incremental-refresh:{ASKER_ID}")
    await Incremental.refresh.invoke(_cog(engine), interaction, [str(ASKER_ID)])

    (update,) = discord_client.interaction_responses()
    assert update["type"] == 7


async def test_buy_button_updates_the_message(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = make_component_interaction(f"incremental-buy:{ASKER_ID}:digger")
    await Incremental.buy.invoke(_cog(engine), interaction, [str(ASKER_ID), "digger"])

    (update,) = discord_client.interaction_responses()
    assert update["type"] == 7
    assert "Digger x1" in [field["name"] for field in update["data"]["embeds"][0]["fields"]]


async def test_buy_button_without_enough_currency_is_refused_privately(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    interaction = make_component_interaction(f"incremental-buy:{ASKER_ID}:gem_cutter")
    await Incremental.buy.invoke(_cog(engine), interaction, [str(ASKER_ID), "gem_cutter"])

    (response,) = discord_client.interaction_responses()
    assert response["data"]["flags"] == 64
    assert "You need" in response["data"]["content"]


@pytest.mark.parametrize("handler", ["refresh", "buy"])
async def test_only_the_owner_can_use_the_buttons(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
    handler: str,
) -> None:
    args = ["999"] if handler == "refresh" else ["999", "digger"]
    interaction = make_component_interaction(f"incremental-{handler}:{':'.join(args)}")
    await getattr(Incremental, handler).invoke(_cog(engine), interaction, args)

    (response,) = discord_client.interaction_responses()
    assert response["data"]["flags"] == 64
    with Session(engine) as session:
        assert session.exec(alive(IncrementalSave)).all() == []
