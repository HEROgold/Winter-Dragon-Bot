from datetime import datetime

from sqlmodel import Field, SQLModel


class SteamSale(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field()
    url: str = Field()
    sale_percent: int = Field()
    final_price: int = Field()
    is_dlc: bool = Field()
    is_bundle: bool = Field()
    update_datetime: datetime = Field()
