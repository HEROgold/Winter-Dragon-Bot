"""Module to Notify users about Steam sales."""

from collections.abc import Iterable
from datetime import datetime
from textwrap import dedent

from discord import Embed
from herogold.log import LoggerMixin
from sqlmodel import Session, select

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.settings import Settings
from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties
from winter_dragon.database.tables.steamuser import SteamUsers


def _filter_date(sale: SteamSale) -> datetime:
    return sale.update_datetime


class SteamSaleNotifier(LoggerMixin):
    """Steam Sale Notifier class."""

    _empty_embed = Embed()

    def __init__(self, bot: WinterDragon, session: Session) -> None:
        """Initialize the Steam Sale Notifier."""
        self._validated = False
        self.bot = bot
        self.session = session
        self.embed = self._empty_embed
        self.users: set[SteamUsers] = set()
        self.sales: set[SteamSale] = set()

    def set_messages(self, sub_mention_remove: str, sub_mention_show: str, disable_message: str, all_sale_message: str) -> None:
        """Add messages to the embed."""
        self.sub_mention_remove = sub_mention_remove
        self.sub_mention_show = sub_mention_show
        self.disable_message = disable_message
        self.all_sale_message = all_sale_message

    def add_users(self, users: Iterable[SteamUsers]) -> None:
        """Add a user to the list of users to notify."""
        self.logger.debug(f"Adding users to notify, {users=}")
        if not users:
            return
        self.users.update(users)

    def add_sales(self, sales: Iterable[SteamSale]) -> None:
        """Add multiple sales to the notifier."""
        self.logger.debug(f"Adding sales to embed, {sales=}")
        if not sales:
            return
        self.sales.update(sales)

    def build_embed(self, embed: Embed) -> Embed | None:
        """Add the tracked sales to the embed. Embed is automatically send to users when notifying."""
        self.embed = embed
        sales_by_youngest = sorted(self.sales, key=_filter_date, reverse=True)
        for i, sale in enumerate(sales_by_youngest):
            properties = self.session.exec(
                select(SteamSaleProperties).where(SteamSaleProperties.steam_sale_id == sale.id),
            ).all()
            install_url = f"{Settings.steam_redirect}/install/{SteamURL(sale.url).app_id}"
            embed_text = f"""
                [{sale.title}]({sale.url})
                Sale: {sale.sale_percent}%
                Price: {sale.final_price}
                Dlc: {SaleTypes.DLC in {prop.property for prop in properties}}
                Bundle: {SaleTypes.BUNDLE in {prop.property for prop in properties}}
                Last Checked: <t:{int(sale.update_datetime.timestamp())}:F>
                Install game: [Click here]({install_url})
            """
            self.embed.add_field(
                name=f"Game {i + 1}",
                value=dedent(embed_text),
                inline=False,
            )
            self.logger.debug(f"Populated embed with: {sale=}")

        max_embed_length = 6000
        while len(str(self.embed.to_dict())) >= max_embed_length:
            self.logger.debug(f"size: {len(str(self.embed.to_dict()))}, removing to decrease size: {self.embed.fields[-1]=}")
            self.embed.remove_field(-1)

        self.logger.debug(f"Build notification embed: {self.embed}")
        self.already_built = True

    def _validate_embed(self) -> None:
        """Check if the embed is valid."""
        if self.embed is self._empty_embed:
            msg = "Embed has not been built. use `.build_embed()` to build the embed before notifying."
            raise ValueError(msg)
        if len(self.embed.fields) == 0:
            msg = "Embed has no fields. use `.add_sales()` to add sales before building the embed."
            raise ValueError(msg)

    def _validate_messages(self) -> None:
        if not self.sub_mention_remove:
            msg = "Missing value for sub_mention_remove. use `.set_messages()` to set these."
            raise ValueError(msg)
        if not self.sub_mention_show:
            msg = "Missing value for sub_mention_show. use `.set_messages()` to set these."
            raise ValueError(msg)
        if not self.disable_message:
            msg = "Missing value for disable_message. use `.set_messages()` to set these."
            raise ValueError(msg)
        if not self.all_sale_message:
            msg = "Missing value for all_sale_message. use `.set_messages()` to set these."
            raise ValueError(msg)

    @property
    def validated(self) -> bool:
        """Check if the messages are validated."""
        if not self._validated:
            self._validate_embed()
            self._validate_messages()
            self._validated = True
        return self._validated

    async def notify(self) -> None:
        """Notify all users about the sales."""
        for user in self.users:
            await self.notify_user(user)

    async def notify_user(self, user: SteamUsers) -> None:
        """Notify a user about the sales."""
        self.logger.debug(f"Showing new sales to {user=}")
        if self.validated:
            self.logger.debug(f"Showing {user}, {self.embed}")
            discord_user = self.bot.get_user(user.user_id) or await self.bot.fetch_user(user.user_id)
            await discord_user.send(content=f"{self.disable_message}\n{self.all_sale_message}", embed=self.embed)
        else:
            self.logger.debug(f"Not showing sales, empty embed fields: {user}, {self.embed}")
