"""Database tables for Steam sales and the users subscribed to them."""

from __future__ import annotations

from datetime import datetime, timedelta
lazy from enum import StrEnum, auto

from sqlalchemy import BigInteger, UniqueConstraint
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.model import DiscordID, SQLModel

from winter_dragon.cogs.steam.urls import SteamURL


class SaleTypes(StrEnum):
    """What kind of store item a sale is for, beyond a plain game."""

    DLC = auto()
    BUNDLE = auto()


class SteamSale(SQLModel, table=True):
    """A Steam store item on sale; ``id`` is its Steam app (or bundle/sub) ID."""

    title: str
    url: str
    sale_percent: int
    final_price: float
    update_datetime: datetime = Field(sa_type=AwareDateTime)
    """When the sale was last seen on Steam."""
    discovered_at: datetime = Field(sa_type=AwareDateTime)
    """When the sale was first seen, or seen again after being outdated; decides who still gets notified of it."""
    sale_end: datetime | None = Field(default=None, sa_type=AwareDateTime)
    """When Steam says the sale ends, if known; the sale is checked again shortly after."""

    @property
    def steam_url(self) -> SteamURL:
        """The sale's store page."""
        return SteamURL(self.url)

    def is_outdated(self, after: timedelta, now: datetime) -> bool:
        """Whether the sale hasn't been seen on Steam for at least ``after``."""
        return self.update_datetime + after <= now


class SteamSaleProperties(SQLModel, table=True):
    """One :class:`SaleTypes` a sale has."""

    steam_sale_id: int = Field(foreign_key="steamsale.id", sa_type=BigInteger)
    property: SaleTypes

    __table_args__ = (UniqueConstraint("steam_sale_id", "property"),)


class SteamUsers(DiscordID, table=True):
    """A Discord user subscribed to Steam sale DMs; ``id`` is their Discord user ID."""

    sale_threshold: int = 100
    """The minimum discount percentage a sale needs before the user is notified."""
    last_notification: datetime = Field(sa_type=AwareDateTime)
    """When the user was last notified; only sales discovered after it are sent."""


STEAM_TABLES = (SteamSale, SteamSaleProperties, SteamUsers)
"""Every table the Steam cog creates on load."""
