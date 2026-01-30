from datetime import UTC, datetime, timedelta
from enum import Enum, auto

from sqlalchemy import text
from sqlmodel import Field

from winter_dragon.database.constants import session
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key


class SaleTypes(Enum):
    DLC = auto()
    BUNDLE = auto()


class SteamSale(SQLModel, table=True):
    title: str
    url: str
    sale_percent: int
    final_price: float
    update_datetime: datetime

    def __hash__(self) -> int:
        return hash((self.title, self.url, self.sale_percent, self.final_price))

    def is_outdated(self, seconds: int) -> bool:
        """Check if a sale has recently updated within the given time frame."""
        return self.update_datetime.astimezone(UTC) + timedelta(seconds=seconds) <= datetime.now(tz=UTC)


class SteamSaleProperties(SQLModel, table=True):
    """associate sale types"""

    steam_sale_id: int = Field(foreign_key=get_foreign_key(SteamSale))
    property: SaleTypes


def migrate_steam_sale_properties() -> None:
    """Migrate existing SteamSale entries to SteamSaleProperties."""
    for sale in SteamSale.get_all():
        if sale.id is None:
            continue
        properties = []
        if getattr(sale, "is_dlc", False):
            properties.append(SaleTypes.DLC)
        if getattr(sale, "is_bundle", False):
            properties.append(SaleTypes.BUNDLE)
        for prop in properties:
            new_property = SteamSaleProperties(steam_sale_id=sale.id, property=prop)
            session.add(new_property)
    # remove is_dlc, and is_bundle from SteamSale, altering table.
    query = text("""
        ALTER TABLE steam_sale
        DROP COLUMN is_dlc,
        DROP COLUMN is_bundle
    """)
    session.connection().execute(query)
    session.commit()
