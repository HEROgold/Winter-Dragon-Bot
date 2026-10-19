"""Unit tests: the lifecycle model's soft delete, create-or-restore, ownership chain and column migration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

import pytest
from sqlalchemy import BigInteger, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session
from wd_db.errors import AlreadyExistsError
from wd_db.extension.lifecycle import (
    LifecycleModel,
    Ownership,
    Through,
    alive,
    create_or_restore,
    ensure_lifecycle_columns,
    lifecycle_models,
    owned_by,
    soft_delete,
)


if TYPE_CHECKING:
    from sqlalchemy import Engine


class LifecycleBoard(LifecycleModel, table=True):
    """A guild's board, owned by its member creator: the top of an ownership chain."""

    ownership: ClassVar[Ownership] = Ownership(member="owner_id", guild="guild_id")
    natural_key: ClassVar[tuple[str, ...]] = ("guild_id", "name")

    guild_id: int = Field(sa_type=BigInteger)
    owner_id: int = Field(sa_type=BigInteger)
    name: str
    topic: str = ""


class LifecycleList(LifecycleModel, table=True):
    """A list on a board, owned through it."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("board_id", LifecycleBoard))

    board_id: int = Field(sa_type=BigInteger, foreign_key="lifecycleboard.id")


class LifecycleCard(LifecycleModel, table=True):
    """A card on a list, owned through the list and so through the board."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("list_id", LifecycleList))

    list_id: int = Field(sa_type=BigInteger, foreign_key="lifecyclelist.id")
    text: str


class LifecycleVote(LifecycleModel, table=True):
    """A member's vote on a card: owned by its member, and through the card by the board's guild."""

    ownership: ClassVar[Ownership] = Ownership(member="voter_id", through=Through("card_id", LifecycleCard))

    card_id: int = Field(sa_type=BigInteger, foreign_key="lifecyclecard.id")
    voter_id: int = Field(sa_type=BigInteger)


class LifecycleSeat(LifecycleModel, table=True):
    """A guild's seat of some kind: one alive per guild and kind, replaced rather than restored."""

    alive_unique: ClassVar[tuple[str, ...]] = ("guild_id", "kind")

    guild_id: int = Field(sa_type=BigInteger)
    kind: str


class LifecycleSale(LifecycleModel, table=True):
    """Shared data, owned by no one."""

    title: str


def _board(name: str = "plans", topic: str = "", guild_id: int = 1, owner_id: int = 3) -> LifecycleBoard:
    return LifecycleBoard(guild_id=guild_id, owner_id=owner_id, name=name, topic=topic)


def _stored(engine: Engine, row: LifecycleModel) -> int:
    with Session(engine) as session:
        stored = create_or_restore(session, row)
        session.commit()
        assert stored.id is not None
        return stored.id


def _alive_boards(engine: Engine) -> list[tuple[str, str]]:
    with Session(engine) as session:
        return [(board.name, board.topic) for board in session.exec(alive(LifecycleBoard))]


def _soft_delete(engine: Engine, board_id: int) -> None:
    with Session(engine) as session:
        board = session.get(LifecycleBoard, board_id)
        assert board is not None
        soft_delete(session, board)
        session.commit()


def test_soft_delete_hides_a_row_from_alive(engine: Engine) -> None:
    board_id = _stored(engine, _board("gone"))
    _stored(engine, _board("kept"))

    _soft_delete(engine, board_id)

    assert _alive_boards(engine) == [("kept", "")]


def test_soft_deleted_row_is_hidden_from_the_default_query(engine: Engine) -> None:
    _soft_delete(engine, _stored(engine, _board()))

    with Session(engine) as session:
        assert session.exec(LifecycleBoard.query).all() == []


def test_create_or_restore_restores_by_id_and_overwrites_fields(engine: Engine) -> None:
    board_id = _stored(engine, _board(topic="old"))
    _soft_delete(engine, board_id)

    restored_id = _stored(engine, LifecycleBoard(id=board_id, guild_id=1, owner_id=3, name="renamed", topic="new"))

    assert restored_id == board_id
    assert _alive_boards(engine) == [("renamed", "new")]


def test_create_or_restore_restores_by_natural_key_and_overwrites_fields(engine: Engine) -> None:
    board_id = _stored(engine, _board(topic="old"))
    _soft_delete(engine, board_id)

    assert _stored(engine, _board(topic="new", owner_id=4)) == board_id

    with Session(engine) as session:
        (board,) = session.exec(owned_by(LifecycleBoard, member=4))
    assert (board.topic, board.deleted_at) == ("new", None)


def test_alive_duplicate_conflicts(engine: Engine) -> None:
    board_id = _stored(engine, _board())

    with Session(engine) as session, pytest.raises(AlreadyExistsError):
        create_or_restore(session, _board(topic="again"))
    with Session(engine) as session, pytest.raises(AlreadyExistsError):
        create_or_restore(session, LifecycleBoard(id=board_id, guild_id=2, owner_id=3, name="other"))


def test_ownership_through_two_parents_resolves_to_the_top_owner(engine: Engine) -> None:
    mine = _stored(engine, _board("mine", owner_id=3, guild_id=1))
    theirs = _stored(engine, _board("theirs", owner_id=4, guild_id=2))
    my_list = _stored(engine, LifecycleList(board_id=mine))
    their_list = _stored(engine, LifecycleList(board_id=theirs))
    _stored(engine, LifecycleCard(list_id=my_list, text="my card"))
    _stored(engine, LifecycleCard(list_id=their_list, text="their card"))

    with Session(engine) as session:
        assert [card.text for card in session.exec(owned_by(LifecycleCard, member=3))] == ["my card"]
        assert [card.text for card in session.exec(owned_by(LifecycleCard, guild=2))] == ["their card"]


def test_owned_by_finds_a_member_on_the_row_and_a_guild_through_its_parents(engine: Engine) -> None:
    board_id = _stored(engine, _board(guild_id=2, owner_id=3))
    list_id = _stored(engine, LifecycleList(board_id=board_id))
    card_id = _stored(engine, LifecycleCard(list_id=list_id, text="card"))
    _stored(engine, LifecycleVote(card_id=card_id, voter_id=9))

    with Session(engine) as session:
        assert [vote.voter_id for vote in session.exec(owned_by(LifecycleVote, member=9, guild=2))] == [9]
        assert session.exec(owned_by(LifecycleVote, member=3)).all() == []  # the board's owner didn't vote
        assert session.exec(owned_by(LifecycleVote, guild=1)).all() == []


def test_alive_unique_allows_a_replacement_of_a_soft_deleted_row(engine: Engine) -> None:
    first = _stored(engine, LifecycleSeat(guild_id=1, kind="chair"))
    with Session(engine) as session:
        old = session.get(LifecycleSeat, first)
        assert old is not None
        soft_delete(session, old)
        session.commit()

    second = _stored(engine, LifecycleSeat(guild_id=1, kind="chair"))

    assert second != first  # a new row, not the old one restored
    with Session(engine) as session, pytest.raises(IntegrityError):
        session.add(LifecycleSeat(guild_id=1, kind="chair"))
        session.commit()


def test_owned_by_with_deleted_rows_finds_soft_deleted_ones_through_a_soft_deleted_parent(engine: Engine) -> None:
    board_id = _stored(engine, _board(guild_id=2))
    list_id = _stored(engine, LifecycleList(board_id=board_id))
    _stored(engine, LifecycleCard(list_id=list_id, text="card"))
    with Session(engine) as session:
        for row in (*session.exec(owned_by(LifecycleCard, guild=2)), *session.exec(owned_by(LifecycleList, guild=2))):
            soft_delete(session, row)
        session.commit()
    _soft_delete(engine, board_id)

    with Session(engine) as session:
        assert session.exec(owned_by(LifecycleCard, guild=2)).all() == []
        assert [card.text for card in session.exec(owned_by(LifecycleCard, guild=2, include_deleted=True))] == ["card"]


def test_soft_delete_at_a_given_moment_stamps_that_moment(engine: Engine) -> None:
    board_id = _stored(engine, _board())
    moment = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)

    with Session(engine) as session:
        board = session.get(LifecycleBoard, board_id)
        assert board is not None
        soft_delete(session, board, at=moment)
        session.commit()

    with Session(engine) as session:
        (board,) = session.exec(owned_by(LifecycleBoard, guild=1, include_deleted=True))
    assert board.deleted_at == moment


def test_owned_by_matches_nothing_for_an_undeclared_owner(engine: Engine) -> None:
    _stored(engine, _board())
    _stored(engine, LifecycleSale(title="cheap game"))

    with Session(engine) as session:
        assert session.exec(owned_by(LifecycleSale, member=3)).all() == []
        assert [sale.title for sale in session.exec(owned_by(LifecycleSale))] == ["cheap game"]


def test_lifecycle_models_yields_every_table() -> None:
    assert {LifecycleBoard, LifecycleList, LifecycleCard} <= set(lifecycle_models())


def test_ensure_lifecycle_columns_migrates_an_old_table() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE lifecycleboard"
                " (id INTEGER PRIMARY KEY, guild_id INTEGER, owner_id INTEGER, name VARCHAR, topic VARCHAR)",
            ),
        )
        connection.execute(text("INSERT INTO lifecycleboard VALUES (1, 1, 3, 'old', '')"))

    ensure_lifecycle_columns(engine, LifecycleBoard, LifecycleList)
    ensure_lifecycle_columns(engine, LifecycleBoard)

    assert _alive_boards(engine) == [("old", "")]
    _soft_delete(engine, 1)
    assert _alive_boards(engine) == []
    with Session(engine) as session:
        session.add(_board("old", owner_id=4))
        with pytest.raises(IntegrityError):
            session.commit()
