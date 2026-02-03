from __future__ import annotations

from sqlmodel import Field

from winter_dragon.database.extension.model import SQLModel


class Generators(SQLModel, table=True):
    """Table for storing generator data."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = Field(default="")
    cost_amount: int = Field(default=100)
    cost_currency: str = Field(default="gold")
    base_per_second: float = Field(default=0.0)
