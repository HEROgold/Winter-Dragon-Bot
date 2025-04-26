from datetime import UTC, datetime, timedelta

from sqlmodel import Field, Session, SQLModel, select


class SteamSale(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    title: str
    url: str
    sale_percent: int
    final_price: float
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime


    def update(self, session: Session) -> bool:
        """Update/override a sale record in Database."""
        if known := session.exec(select(SteamSale).where(SteamSale.id == self.id).with_for_update()).first():
            known.title = self.title
            known.url = self.url
            known.sale_percent = self.sale_percent
            known.final_price = self.final_price
            known.is_dlc = self.is_dlc
            known.is_bundle = self.is_bundle
            known.update_datetime = self.update_datetime
            session.add(known)
            session.commit()
            return True
        return False

    def is_outdated(self, session: Session, seconds: int) -> bool:
        """Check if a sale has recently been updated."""
        if known := session.exec(select(SteamSale).where(SteamSale.id == self.id)).first():
            update_period_date = known.update_datetime + timedelta(seconds=seconds)
            return update_period_date <= datetime.now(tz=UTC)
        msg = "Sale not found in database"
        raise ValueError(msg)
