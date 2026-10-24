"""Custom data is read and replaced through the caller's session, and only committed by the caller."""

import pytest
from sqlmodel import Session, select

from wd_db.extension.custom_data import CustomData, get_custom_data, set_custom_data
from wd_db.extension.lifecycle import DiscordKeyedModel
from wd_db.testing import sqlite_engine


class CustomDataOwner(DiscordKeyedModel, table=True):
    """A table for these tests only."""

    name: str = ""


@pytest.fixture
def session() -> Session:
    session = Session(sqlite_engine())
    owner = CustomDataOwner(id=1)
    session.add(owner)
    session.flush()
    return session


def owner(session: Session) -> CustomDataOwner:
    stored = session.get(CustomDataOwner, 1)
    assert stored is not None
    return stored


def test_a_row_without_custom_data_reads_empty(session: Session) -> None:
    assert get_custom_data(session, owner(session)) == {}


def test_set_then_get_round_trips(session: Session) -> None:
    set_custom_data(session, owner(session), {"clan": None, "version": 3})

    assert get_custom_data(session, owner(session)) == {"clan": None, "version": 3}


def test_setting_again_replaces_and_drops_the_old_blob(session: Session) -> None:
    set_custom_data(session, owner(session), {"version": 1})
    set_custom_data(session, owner(session), {"version": 2})

    assert get_custom_data(session, owner(session)) == {"version": 2}
    assert len(session.exec(select(CustomData)).all()) == 1


def test_empty_data_removes_it(session: Session) -> None:
    set_custom_data(session, owner(session), {"version": 1})
    set_custom_data(session, owner(session), {})

    assert get_custom_data(session, owner(session)) == {}
    assert session.exec(select(CustomData)).all() == []


def test_nothing_is_committed(session: Session) -> None:
    set_custom_data(session, owner(session), {"version": 1})
    session.rollback()

    assert session.exec(select(CustomData)).all() == []
