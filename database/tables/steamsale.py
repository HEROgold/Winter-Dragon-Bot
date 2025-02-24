from datetime import datetime

from sqlmodel import Field, SQLModel


class SteamSale(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    title: str
    url: str
    sale_percent: int
    final_price: int
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime
