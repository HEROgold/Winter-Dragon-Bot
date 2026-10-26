"""Database tables of the Incremental game. A save is one member's, whatever guild they play in."""

from datetime import datetime
lazy from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel, Ownership, Through


class IncrementalSave(DiscordKeyedModel, table=True):
    """A member's save; ``id`` is their Discord user ID, and they own it."""

    ownership: ClassVar[Ownership] = Ownership(member="id")

    settled_at: datetime = Field(sa_type=AwareDateTime)
    """When the stored balances were last brought up to date; production since then is added when the save is read."""


class SaveBalance(LifecycleModel, table=True):
    """How much of one currency a save held at its ``settled_at``."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("save_id", IncrementalSave))
    natural_key: ClassVar[tuple[str, ...]] = ("save_id", "currency")

    save_id: int = Field(foreign_key="incrementalsave.id", sa_type=BigInteger)
    currency: str
    """The :class:`~winter_dragon.cogs.incremental.catalogue.CurrencyKey`."""
    amount: float


class SaveGenerator(LifecycleModel, table=True):
    """How many of one generator a save owns."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("save_id", IncrementalSave))
    natural_key: ClassVar[tuple[str, ...]] = ("save_id", "generator")

    save_id: int = Field(foreign_key="incrementalsave.id", sa_type=BigInteger)
    generator: str
    """The :class:`~winter_dragon.cogs.incremental.catalogue.GeneratorKey`."""
    owned: int = Field(ge=0)


INCREMENTAL_TABLES = (IncrementalSave, SaveBalance, SaveGenerator)
"""Every table the Incremental cog creates on load."""
