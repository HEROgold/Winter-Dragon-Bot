"""Shared fixtures for the wd-bot test suite: an in-memory database and an interaction builder."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Protocol

lazy import pytest
lazy from sqlalchemy import BigInteger
lazy from sqlalchemy.ext.compiler import compiles
lazy from sqlalchemy.pool import StaticPool
lazy from sqlmodel import SQLModel, create_engine
lazy from wd_discord.gateway.events import Interaction, InteractionData, InteractionType
lazy from wd_discord.resources.user import User


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from sqlalchemy import Engine
    lazy from wd_discord.gateway.events import InteractionDataOption, ResolvedData


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(_type: BigInteger, _compiler: object, **_kwargs: object) -> str:
    """Render BigInteger as INTEGER on sqlite.

    wd_db's SQLModel.id is a BigInteger primary key, which sqlite only autoincrements when the
    column type is exactly INTEGER. Postgres (production) is unaffected.
    """
    return "INTEGER"


@pytest.fixture
def engine() -> Engine:
    """Return an in-memory sqlite engine with every table created, shared across threads."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


class InteractionFactory(Protocol):
    """Builds an application-command interaction, as the ``make_interaction`` fixture returns."""

    def __call__(
        self,
        name: str = "c",
        *,
        options: Sequence[InteractionDataOption] = (),
        resolved: ResolvedData | None = None,
        user: User | None = ...,
    ) -> Interaction:
        """Build the interaction."""
        ...


ASKER = User.model_validate({"id": "3", "username": "asker", "discriminator": "0"})
"""The default invoking user of :func:`make_interaction`."""


@pytest.fixture
def make_interaction() -> InteractionFactory:
    """Return a builder for a ``/name`` interaction with the given options, invoked by ``user``."""

    def build(
        name: str = "c",
        *,
        options: Sequence[InteractionDataOption] = (),
        resolved: ResolvedData | None = None,
        user: User | None = ASKER,
    ) -> Interaction:
        return Interaction(
            id="1",
            application_id="2",
            type=InteractionType.APPLICATION_COMMAND,
            token="tok",  # noqa: S106
            version=1,
            user=user,
            data=InteractionData(id="10", name=name, type=1, options=list(options), resolved=resolved),
        )

    return build
