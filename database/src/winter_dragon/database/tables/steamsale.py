from datetime import UTC, datetime, timedelta

from sqlmodel import Field, Session, select
from winter_dragon.database.extension.model import SQLModel


class SteamSale(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    title: str
    url: str
    sale_percent: int
    final_price: float
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime

    def is_outdated(self, session: Session, seconds: int) -> bool:
        """Check if a sale has recently been updated."""
        if known := session.exec(select(SteamSale).where(SteamSale.id == self.id)).first():
            update_period_date = known.update_datetime.astimezone(UTC) + timedelta(seconds=seconds)
            return update_period_date <= datetime.now(tz=UTC)
        msg = "Sale not found in database"
        raise ValueError(msg)
