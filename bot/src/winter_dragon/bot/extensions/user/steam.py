import asyncio
import datetime
import re
from collections.abc import AsyncGenerator, Sequence
from contextlib import suppress
from textwrap import dedent
from typing import Any, cast

import bs4
import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot._types.dicts import Sale
from winter_dragon.bot.config import config
from winter_dragon.bot.constants import (
    BUNDLE_DISCOUNT,
    BUNDLE_FINAL_PRICE,
    BUNDLE_LINK,
    BUNDLE_TITLE,
    CURRENCY_LABELS,
    DATA_APPID,
    DISCOUNT_FINAL_PRICE,
    DISCOUNT_PERCENT,
    DISCOUNT_PRICES,
    GAME_BUY_AREA,
    SEARCH_GAME_TITLE,
    SINGLE_GAME_TITLE,
    STEAM_PERIOD,
    STEAM_SEND_PERIOD,
    WEBSITE_URL,
)
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.tasks import loop
from winter_dragon.database import Session
from winter_dragon.database.tables import SteamSale, SteamUser, User

from bot.src.WinterDragon.bot.config import Config


class Steam(GroupCog):
    async def cog_load(self) -> None:
        self.update.start()
        self.loop = asyncio.get_event_loop()

    async def get_htl(self, url: str) -> requests.Response:
        return await self.loop.run_in_executor(None, requests.get, url)


    @app_commands.command(name="add", description="Get notified automatically about free steam games")
    async def slash_add(self, interaction:discord.Interaction) -> None:
        with self.session as session:
            if session.exec(select(User).where(User.id == interaction.user.id)).first() is None:
                session.add(User(id = interaction.user.id))
                session.commit()

            result = session.exec(select(SteamUser).where(SteamUser.id == interaction.user.id))
            if result.first():
                await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
                return
            session.add(SteamUser(id = interaction.user.id))
            session.commit()
        sub_mention = self.get_command_mention(self.slash_show)
        msg = f"I will notify you of new steam games!\nUse {sub_mention} to view current sales."
        await interaction.response.send_message(msg, ephemeral=True)


    @app_commands.command(name="remove", description="No longer get notified of free steam games")
    async def slash_remove(self, interaction:discord.Interaction) -> None:
        with self.session as session:
            result = session.exec(select(SteamUser).where(SteamUser.id == interaction.user.id))
            user = result.first()
            if not user:
                await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
                return
            session.delete(user)
            session.commit()
        await interaction.response.send_message("I not notify you of new free steam games anymore.", ephemeral=True)


    # @app_commands.checks.cooldown(1, UPDATE_PERIOD)
    @app_commands.command(
        name="show",
        description="Get a list of steam games that are on sale for the given percentage or higher")
    async def slash_show(self, interaction: discord.Interaction, percent: int = 100) -> None:
        await interaction.response.defer()

        embed = discord.Embed(title="Steam Games", description=f"Steam Games with sales {percent}% or higher", color=0x094d7f)
        embed = self.populate_embed(embed, await self.get_steam_sales(percent))
        self.logger.debug(f"{embed.to_dict()}")

        if len(embed.fields) > 0:
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"No steam games found with {percent} or higher sales.", ephemeral=True)


    @loop(seconds=STEAM_SEND_PERIOD)
    async def update(self) -> None:
        """Create a discord Embed object to send and notify users of new 100% sales.

        Expected amount of sales should be low enough it'll never reach embed size limit.
        """
        self.logger.info("updating sales")

        embed = discord.Embed(title="Free Steam Game's", description="New free Steam Games have been found!", color=0x094d7f)
        new_sales = await self.get_new_steam_sales(percent=100)
        self.logger.debug(f"{new_sales=}")
        embed = self.populate_embed(embed, new_sales)

        if embed is None:
            self.logger.warning("Got no populated embed, skipping sale sending.")
            return

        sub_mention_remove = self.get_command_mention(self.slash_remove)
        sub_mention_show = self.get_command_mention(self.slash_show)
        disable_message = f"You can disable this message by using {sub_mention_remove}"
        all_sale_message = f"You can see other sales by using {sub_mention_show}, followed by a percentage"

        with self.session as session:
            users = session.exec(select(SteamUser)).all()
            self.logger.debug(f"Got embed with sales, {embed}, to send to {users=}")

            for db_user in users:
                self.logger.debug(f"Trying to show new sales to {db_user.id=}")
                try:
                    user = self.bot.get_user(db_user.id) or await self.bot.fetch_user(db_user.id)
                except discord.errors.NotFound:
                    self.logger.warning(f"Not showing {db_user.id=} sales, discord.errors.NotFound")
                    continue

                if len(embed.fields) > 0:
                    self.logger.debug(f"Showing {user}, {embed}")
                    await user.send(content=f"{disable_message}\n{all_sale_message}", embed=embed)
                else:
                    self.logger.debug(f"Not showing sales, empty embed fields: {user}, {embed}")


    @update.before_loop
    async def before_update(self) -> None:
        await self.bot.wait_until_ready()


    def populate_embed(self, embed: discord.Embed, sales: list[Sale]) -> discord.Embed:
        """Fill a given embed with sales, and then returns the populated embed."""
        if not sales:
            return embed

        with suppress(AttributeError):
            # Sort on sale percentage (int), so reverse to get highest first
            sales.sort(key=lambda x: x["sale_percent"], reverse=True)

        for i, sale in enumerate(sales):
            install_url = f"{WEBSITE_URL}/redirect?redirect_url=steam://install/{self.get_id_from_game_url(sale['url'])}"
            embed_text = f"""
                [{sale['title']}]({sale["url"]})
                Sale: {sale["sale_percent"]}%
                Price: {sale["final_price"]}
                Dlc: {sale["is_dlc"]}
                Bundle: {sale["is_bundle"]}
                Last Checked: <t:{int(sale["update_datetime"].timestamp())}:F>
                Install game: [Click here]({install_url})
            """
            embed.add_field(
                name = f"Game {i+1}",
                value = dedent(embed_text),
                inline = False,
            )
            self.logger.debug(f"Populated embed with: {sale=}")

        # embed size above 6000 characters.
        max_embed_length = 6000
        while len(str(embed.to_dict())) >= max_embed_length:
            self.logger.debug(f"size: {len(str(embed.to_dict()))}, removing to decrease size: {embed.fields[-1]=}")
            embed.remove_field(-1)

        self.logger.debug(f"Returning {embed}")
        return embed


    async def get_updated_sales(self, sales: Sequence[SteamSale] | Sequence[Sale]) -> list[Sale]:
        # sourcery skip: assign-if-exp, reintroduce-else
        """Return a new list of sales, based of a given list of sales.

        Args:
        ----
            sales (list[SteamSale]): Old list to run checks on

        Returns:
        -------
            list[SteamSale]: New list that gets returned

        """
        # convert to Sale for each element that is SteamSale
        known_sales: list[Sale] = [
            self.SteamSale_to_Sale(i)
            if isinstance(i, SteamSale)
            else i
            for i in sales
        ]

        updated_sales: list[Sale] = []
        for sale in known_sales:
            if self.is_outdated(sale):
                updated_sales.append(await self.get_game_sale(sale["url"]))
            else:
                updated_sales.append(sale)

        self.logger.debug(f"{updated_sales=}")
        if known_sales == updated_sales:
            return known_sales
        return updated_sales


    def is_outdated(self, sale: SteamSale | Sale) -> bool:
        """Check if a sale has recently been updated.

        Args:
        ----
            sale (SteamSale | Sale): The sale to check against

        Returns:
        -------
            bool: True, False

        """
        if isinstance(sale, SteamSale):
            update_period_date = sale.update_datetime + datetime.timedelta(seconds=STEAM_PERIOD)
        else:
            update_period_date = sale["update_datetime"] + datetime.timedelta(seconds=STEAM_PERIOD)

        return (
            update_period_date
            <= datetime.datetime.now()  # noqa: DTZ005
        )


    def get_saved_sales(self) -> Sequence[SteamSale]:
        """Get saved/known sales from winter_dragon.database.

        Returns
        -------
            list[SteamSale]: List of SteamSale database objects

        """
        with self.session as session:
            sales = session.exec(select(SteamSale)).all()
        self.logger.debug(f"saved {sales=}")
        return sales


    def get_id_from_game_url(self, url: str) -> int:
        """Get an id from a steam game url.

        Args:
        ----
            url (str): Url to extract the id from

        Returns:
        -------
            int: The found id of a game

        """
        # sourcery skip: class-extract-method
        # example: https://store.steampowered.com/app/1168660/Barro_2020/
        regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_game_id, url)
        self.logger.debug(f"game id: {matches=}")
        # return first match as int, or 0
        return int(matches[0]) or 0


    def is_bundle(self, url: str) -> bool:
        """Find out if a url is for a bundle.

        Args:
        ----
            url (str): Url to look through

        Returns:
        -------
            bool: True, False

        """
        # sourcery skip: class-extract-method
        # example: https://store.steampowered.com/bundle/23756/Bundle_with_fun_games/?l=dutch&curator_clanid=4777282
        regex_bundle = r"(?:https?:\/\/)?store\.steampowered\.com\/(bundle)\/\d+\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_bundle, url)
        self.logger.debug(f"bundle: {matches=}")
        return bool(matches)


    def is_valid_game_url(self, url: str) -> bool:
        """Find out if a url is for a valid game.

        Args:
        ----
            url (str): Url to check for

        Returns:
        -------
            bool: True, False

        """
        return bool(self.get_id_from_game_url(url))


    async def get_new_steam_sales(self, percent: int) -> list[Sale]:
        """Get only unknown/new sales.

        Args:
        ----
            percent (int): Percentage to check for

        Returns:
        -------
            list[Sale]: List of TypedDict Sale

        """
        known_sales = [self.SteamSale_to_Sale(i) for i in self.get_saved_sales()]
        steam_sales = [x async for x in self.get_sales_from_steam(percent)]

        self.logger.debug(f"checking for new sales, {known_sales=}, {steam_sales=}")

        outdated = [
            i["title"]
            for i in known_sales
            if self.is_outdated(i)
        ]

        return [
            sale
            for sale in steam_sales
            if sale["title"] in outdated
        ]


    async def get_steam_sales(self, percent: int) -> list[Sale]:
        """Get sales from winter_dragon.database or from website depending on `UPDATE_PERIOD`."""
        updated_sales = await self.get_updated_sales(self.get_saved_sales())
        if updated_sales == []:
            self.logger.debug("getting sales from steam")

            return [i async for i in self.get_sales_from_steam(percent)]
        self.logger.debug("returning known sales")
        return updated_sales


    async def get_games_from_bundle(self, url: str) -> list[Sale]:
        """Get the sales from a bundle.

        Args:
        ----
            url (str): Url of the bundle to get the game sales from

        Raises:
        ------
            ValueError: Error when url is invalid

        Returns:
        -------
            SteamSale: SteamSale database object

        """
        if not self.is_bundle(url):
            msg = "Invalid Steam Bundle URL"
            raise ValueError(msg)

        html = await self.get_htl(url)
        soup = BeautifulSoup(html.text, "html.parser")

        return [
            await self.get_game_sale(sale["href"])
            for sale in soup.find_all("a", class_=BUNDLE_LINK)
        ]


    def SteamSale_to_Sale(self, sale: SteamSale) -> Sale:  # noqa: N802
        """Convert a SteamSale db object to TypedDict Sale.

        Args:
        ----
            sale (SteamSale): SteamSale database object

        Returns:
        -------
            Sale: TypedDict containing the same items as Db object

        """
        with self.session:
            return {
                "title": sale.title,
                "url": sale.url,
                "sale_percent": sale.sale_percent,
                "final_price": sale.final_price,
                "is_dlc": sale.is_dlc,
                "is_bundle": sale.is_bundle,
                "update_datetime": sale.update_datetime,
            }

    @Config.default("Steam", "search_url", "https://store.steampowered.com/search/?sort_by=Price_ASC&specials=1&supportedlang=english")
    async def get_sales_from_steam(self, percent: int) -> AsyncGenerator[Sale, Any]:
        """Scrape sales from https://store.steampowered.com/search/.

        With the search options: Ascending price, Special deals, English.
        """
        html = await self.get_htl(config.get("Steam", "search_url"))
        soup = BeautifulSoup(html.text, "html.parser")

        for sale_tag in soup.find_all(class_=DISCOUNT_PRICES):
            if sale_tag is None:
                continue

            sale_tag: bs4.element.Tag
            discount_perc = sale_tag.parent.find(class_=DISCOUNT_PERCENT)
            a_tag = sale_tag.find_parent("a", href=True)
            href = cast("str", a_tag.get("href"))

            if discount_perc is None: # Check game's page
                yield await self.get_game_sale(href)
                continue

            discount = int(discount_perc.text[1:-1]) # strip the - and % from the tag

            if a_tag is None:
                self.logger.warning(f"Got empty sale: {sale_tag=}, {a_tag=}")

            if discount >= percent:
                price = a_tag.find(class_=DISCOUNT_FINAL_PRICE).text[:-1].replace(",", ".")
                sale = SteamSale(
                    id = a_tag[DATA_APPID],
                    title = a_tag.find(class_=SEARCH_GAME_TITLE).text,
                    url = a_tag["href"],
                    sale_percent = discount,
                    final_price = self.price_to_num(price),
                    is_dlc = False,
                    is_bundle = False,
                    update_datetime = datetime.datetime.now(),  # noqa: DTZ005
                )
                yield self.add_sale(sale, "steam search")


    async def get_bundle_sale(self, url: str) -> Sale:
        # sourcery skip: extract-method
        """Get sale for a bundle.

        Args:
        ----
            url (str): Url of the bundle to get the sale from

        Raises:
        ------
            ValueError: Error when url is invalid

        Returns:
        -------
            SteamSale: SteamSale database object

        """
        if not self.is_bundle(url):
            msg = "Invalid Steam Bundle URL"
            raise ValueError(msg)

        html = await self.get_htl(url)
        soup = BeautifulSoup(html.text, "html.parser")

        price = soup.find(class_=BUNDLE_FINAL_PRICE).text[:-1].replace(",", ".")
        sale = SteamSale(
            id = self.get_id_from_game_url(url),
            title = soup.find(class_=BUNDLE_TITLE).text,
            url = url,
            sale_percent = soup.find(class_=BUNDLE_DISCOUNT).text[:-1], # strip %
            final_price = self.price_to_num(price),
            is_dlc = False,
            is_bundle = True,
            update_datetime = datetime.datetime.now(),  # noqa: DTZ005
        )
        return self.add_sale(sale, "bundle")


    async def get_game_sale(self, url: str) -> Sale:
        """Get a single game sale from specific url."""
        if not self.is_valid_game_url(url):
            msg = "Invalid Steam Game URL"
            raise ValueError(msg)

        html = await self.get_htl(url)
        soup = BeautifulSoup(html.text, "html.parser")

        add_to_cart = soup.find(class_="btn_addtocart")
        buy_area = add_to_cart.find_parent(class_=GAME_BUY_AREA)

        if price := buy_area.find(class_=DISCOUNT_FINAL_PRICE):
            price = price.text[:-1].replace(",", ".")
            title = soup.find(class_=SINGLE_GAME_TITLE).text
            game_id = self.get_id_from_game_url(url)
            sale_perc = buy_area.find(class_=DISCOUNT_PERCENT).text[1:-1] # strip '-' and '%' from sale tag
            final_price = self.price_to_num(price)
            is_dlc = bool(soup.find("div", class_="content"))

            sale = SteamSale(
                id = game_id,
                title = title,
                url = url,
                sale_percent = sale_perc,
                final_price = final_price,
                is_dlc = is_dlc,
                is_bundle = False,
                update_datetime = datetime.datetime.now(),  # noqa: DTZ005
            )
            return self.add_sale(sale, "dlc" if is_dlc else "game")

        if price := buy_area.find(class_="game_purchase_price"):
            self.logger.warning(msg=f"Game not on sale: {url=}")

            price = price.text[:-1].replace(",", ".")
            title = soup.find(class_=SINGLE_GAME_TITLE).text
            game_id = self.get_id_from_game_url(url)
            final_price = self.price_to_num(price)
            is_dlc = bool(soup.find("div", class_="content"))

            return self.add_sale(SteamSale(
                id = game_id,
                title = title,
                url = url,
                sale_percent = 0,
                final_price = final_price,
                is_dlc = is_dlc,
                is_bundle = False,
                update_datetime = datetime.datetime.now(),  # noqa: DTZ005
            ), "dlc" if is_dlc else "game")

        self.logger.warning(f"Got empty price: {url=}")
        msg = "Should not be reached"
        raise NotImplementedError(msg)


    def price_to_num(self, s: str) -> float:
        s = s.strip()
        try:
            return float(s)
        except ValueError:
            return float(s.strip(CURRENCY_LABELS))


    def update_sale(self, sale: SteamSale, session: Session) -> bool:
        """Update/override a sale record in Database.

        Args:
        ----
            session (Session): Session to connect to DataBase
            sale (SteamSale): Sale to update

        Returns:
        -------
            bool: True when updated, False when not updated

        """
        if known := session.exec(select(SteamSale).where(SteamSale.id == sale.id)).first():
            known.title = sale.title
            known.url = sale.url
            known.sale_percent = sale.sale_percent
            known.final_price = sale.final_price
            known.is_dlc = sale.is_dlc
            known.is_bundle = sale.is_bundle
            known.update_datetime = sale.update_datetime
            return True
        return False


    def add_sale(
        self,
        sale: SteamSale | Sale,
        category: str,
    ) -> Sale:
        """Add a sale to db, and return presentable TypedDict. Doesn't commit a given session.

        Args:
        ----
            session (Session): Session for database connection
            sale (SteamSale): SteamSale database object
            category (str): Category where sale was found

        Returns:
        -------
            Sale: TypedDict in presentable format

        """
        with self.session:
            if isinstance(sale, dict): # Assume Sale typeddict
                sale = self.Sale_to_SteamSale(sale)
            if not self.update_sale(sale, self.session):
                self.session.add(sale)
            self.session.commit()

            self.logger.debug(f"Found {category} {sale=}")
            return self.SteamSale_to_Sale(sale)


    def Sale_to_SteamSale(self, sale: Sale) -> SteamSale:  # noqa: N802
        return SteamSale(
            id = self.get_id_from_game_url(sale["url"]),
            title = sale["title"],
            url = sale["url"],
            sale_percent = sale["sale_percent"],
            final_price = sale["final_price"],
            is_dlc = sale["is_dlc"],
            is_bundle = sale["is_bundle"],
            update_datetime = sale["update_datetime"],
        )


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Steam(bot))
