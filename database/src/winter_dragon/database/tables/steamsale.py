from datetime import UTC, datetime, timedelta

from sqlmodel import select
from winter_dragon.database.extension.model import SQLModel


class SteamSale(SQLModel, table=True):

    title: str
    url: str
    sale_percent: int
    final_price: float
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime

    def is_outdated(self, seconds: int) -> bool:
        """Check if a sale has recently updated within the given time frame."""
        return bool(self.session.exec(select(SteamSale).where(
            SteamSale.id == self.id,
            SteamSale.update_datetime.astimezone(UTC) + timedelta(seconds=seconds) <= datetime.now(tz=UTC),
        )).first())
