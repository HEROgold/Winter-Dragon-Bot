"""Module to handle Steam Sale operations."""
from collections.abc import Sequence

from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.log import LoggerMixin
from winter_dragon.database import Session, engine
from winter_dragon.database.tables.steamsale import SteamSale


class SteamSaleRepository(LoggerMixin):
    """Steam Sale model for the bot."""

    def __init__(self, bot: WinterDragon) -> None:
        """Initialize the Steam Sale model."""
        self.bot = bot
        self.session = Session(engine, expire_on_commit=False)

    def get_saved_sales(self) -> Sequence[SteamSale]:
        """Get saved/known sales from winter_dragon.database."""
        return self.session.exec(select(SteamSale)).all()

    def update_sale(
        self,
        sale: SteamSale,
    ) -> None:
        """Add a sale to db, and return presentable TypedDict. Doesn't commit a given session."""
        sale.update(self.session)

    def is_outdated(self, sale: SteamSale, seconds: int) -> bool:
        """Check if a sale has recently been updated."""
        return sale.is_outdated(self.session, seconds)

async def setup(_bot: WinterDragon) -> None:
    """Set up the Steam Sale repository."""
    return
