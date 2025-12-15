"""Module to Notify users about Steam sales."""
from collections.abc import Iterable
from textwrap import dedent

from discord import Embed, Member, NotFound, User
from herogold.log import LoggerMixin
from sqlmodel import Session, select

from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.settings import Settings
from winter_dragon.bot.extensions.user.steam.steam_url import SteamURL
from winter_dragon.database.tables.steamsale import SaleTypes, SteamSale, SteamSaleProperties
from winter_dragon.database.tables.steamuser import SteamUsers


class SteamSaleNotifier(LoggerMixin):
    """Steam Sale Notifier class."""

    def __init__(self, bot: WinterDragon, session: Session, embed: Embed) -> None:
        """Initialize the Steam Sale Notifier."""
        self._validated = False
        self.bot = bot
        self.session = session
        self.embed = embed
        self.users: set[User] = set()

    def set_messages(self, sub_mention_remove: str ,sub_mention_show: str, disable_message: str, all_sale_message: str) -> None:
        """Add messages to the embed."""
        self.sub_mention_remove = sub_mention_remove
        self.sub_mention_show = sub_mention_show
        self.disable_message = disable_message
        self.all_sale_message = all_sale_message

    def add_user(self, user_id: User) -> None:
        """Add a user to the list of users to notify."""
        self.users.add(user_id)

    def add_sales(self, sales: Iterable[SteamSale]) -> None:
        """Add multiple sales to the notifier."""
        self.logger.debug(f"Adding sales to embed, {sales=}")
        if not sales:
            return

        for i, sale in enumerate(sales):
            properties = self.session.exec(
                select(SteamSaleProperties)
                .where(SteamSaleProperties.steam_sale_id == sale.id),
            ).all()
            install_url = f"{Settings.WEBSITE_URL}/redirect?redirect_url=steam://install/{SteamURL(sale.url).id}"
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
                name = f"Game {i+1}",
                value = dedent(embed_text),
                inline = False,
            )
            self.logger.debug(f"Populated embed with: {sale=}")

        # embed size above 6000 characters.
        max_embed_length = 6000
        while len(str(self.embed.to_dict())) >= max_embed_length:
            self.logger.debug(f"size: {len(str(self.embed.to_dict()))}, removing to decrease size: {self.embed.fields[-1]=}")
            self.embed.remove_field(-1)

        self.logger.debug(f"Returning {self.embed}")
        return

    def _is_valid_embed(self) -> bool:
        """Check if the embed is valid."""
        return len(self.embed.fields) == 0

    def _validate_messages(self) -> None:
        if not self.sub_mention_remove:
            msg = "Missing value for sub_mention_remove. use `add_messages()` to add these."
            raise ValueError(msg)
        if not self.sub_mention_show:
            msg = "Missing value for sub_mention_show. use `add_messages()` to add these."
            raise ValueError(msg)
        if not self.disable_message:
            msg = "Missing value for disable_message. use `add_messages()` to add these."
            raise ValueError(msg)
        if not self.all_sale_message:
            msg = "Missing value for all_sale_message. use `add_messages()` to add these."
            raise ValueError(msg)

    @property
    def validated(self) -> bool:
        """Check if the messages are validated."""
        if not self._validated:
            self._is_valid_embed()
            self._validate_messages()
            self._validated = True
        return self._validated

    async def notify_user(self, user: User | Member) -> None:
        """Notify a user about the sales."""
        self.logger.debug(f"Trying to show new sales to {user=}")
        if self.validated:
            self.logger.debug(f"Showing {user}, {self.embed}")
            await user.send(content=f"{self.disable_message}\n{self.all_sale_message}", embed=self.embed)
        else:
            self.logger.debug(f"Not showing sales, empty embed fields: {user}, {self.embed}")

    async def notify_users(self, users: Iterable[User] | None = None) -> None:
        """Notify all users about the sales."""
        await self._add_subscribers()
        for user in users or []:
            self.users.add(user)

        self.logger.debug(f"Got embed with sales, {self.embed}, to send to {self.users=}")
        for user in self.users:
            await self.notify_user(user)

    async def _add_subscribers(self) -> None:
        users = self.session.exec(select(SteamUsers)).all()
        self.logger.debug(f"Got embed with sales, {self.embed}, to send to {users=}")

        for subscribed_user in users:
            self.logger.debug(f"Trying to show new sales to {subscribed_user.user_id=}")
            try:
                self.users.add(self.bot.get_user(subscribed_user.user_id) or await self.bot.fetch_user(subscribed_user.user_id))
            except NotFound:
                self.logger.warning(f"Not showing {subscribed_user.user_id=} sales, discord.errors.NotFound")
                continue
