from datetime import datetime

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
        """Update/override a sale record in Database.

        Args:
        ----
            session (Session): Session to connect to DataBase
            sale (SteamSale): Sale to update

        Returns:
        -------
            bool: True when updated, False when not updated

        """
        if known := session.exec(select(SteamSale).where(SteamSale.id == self.id)).first():
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
