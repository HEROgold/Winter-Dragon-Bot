"""herogold relationship links are read and replaced through the caller's session, and only committed by the caller."""

from __future__ import annotations

import pytest
from herogold.orm.core.utils import Relationship
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel

from wd_db.extension.lifecycle import LifecycleModel
from wd_db.extension.relationships import link, linked


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite, so herogold's BigInteger ids autoincrement."""
    return "INTEGER"


class LinkAccount(LifecycleModel, table=True):
    """A table for these tests only."""

    name: str = ""


class LinkInvite(LifecycleModel, table=True):
    """A table for these tests only, linked to the account that used it."""

    code: str = ""
    used_by = Relationship(LinkAccount)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://", connect_args={"autocommit": False})
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(LinkInvite(code="abc"))
    session.flush()
    return session


def invite(session: Session) -> LinkInvite:
    stored = session.get(LinkInvite, 1)
    assert stored is not None
    return stored


def test_an_unlinked_relationship_reads_none(session: Session) -> None:
    assert linked(session, invite(session), "used_by") is None


def test_link_adds_an_unsaved_target_and_links_it(session: Session) -> None:
    link(session, invite(session), "used_by", LinkAccount(name="martijn"))

    account = linked(session, invite(session), "used_by")
    assert isinstance(account, LinkAccount)
    assert account.name == "martijn"


def test_linking_again_replaces_the_link(session: Session) -> None:
    link(session, invite(session), "used_by", LinkAccount(name="first"))
    link(session, invite(session), "used_by", LinkAccount(name="second"))

    account = linked(session, invite(session), "used_by")
    assert account is not None
    assert account.name == "second"


def test_none_removes_the_link(session: Session) -> None:
    link(session, invite(session), "used_by", LinkAccount(name="first"))
    link(session, invite(session), "used_by", None)

    assert linked(session, invite(session), "used_by") is None


def test_nothing_is_committed(session: Session) -> None:
    link(session, invite(session), "used_by", LinkAccount(name="first"))
    session.rollback()
    session.add(LinkInvite(code="abc"))
    session.flush()

    assert linked(session, invite(session), "used_by") is None


def test_an_unknown_relationship_is_refused(session: Session) -> None:
    with pytest.raises(AttributeError, match="no relationship named 'owner'"):
        linked(session, invite(session), "owner")
