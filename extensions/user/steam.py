import datetime
import re
from textwrap import dedent
from typing import TypedDict, overload
from bs4 import BeautifulSoup
import bs4

import discord
from discord import app_commands
from discord.ext import tasks
import requests

from tools.config_reader import config
from tools.database_tables import SteamSale, SteamUser, User, engine, Session
from _types.cogs import GroupCog
from _types.bot import WinterDragon


# Constant vars that contain tag names to look for
DISCOUNT_FINAL_PRICE = "discount_final_price"
DISCOUNT_PERCENT = "discount_pct"
SEARCH_GAME_TITLE = "title"
DATA_APPID = "data-ds-appid"

GAME_BUY_AREA = "game_area_purchase_game_wrapper"
SINGLE_GAME_TITLE = "apphub_AppName"
GAME_RELEVANT = "block responsive_apppage_details_right heading responsive_hidden"
IS_DLC_RELEVANT_TO_YOU = "Is this DLC relevant to you?"

BUNDLE_TITLE = "pageheader"
BUNDLE_LINK = "tab_item_overlay"
BUNDLE_PRICE = "price bundle_final_package_price"
BUNDLE_DISCOUNT = "price bundle_discount"
BUNDLE_FINAL_PRICE = "price bundle_final_price_with_discount"

DATE_FORMAT = "%Y-%m-%d, %H:%M:%S"

# 3 hour cooldown on html updates
UPDATE_PERIOD = 3600 * 3 


class Sale(TypedDict):
    title: str
    url: str
    sale_percent: int
    final_price: int
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime.datetime


class Steam(GroupCog):
    @app_commands.command(name="add", description="Get notified automatically about free steam games")
    async def slash_add(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            if session.query(User).where(User.id == interaction.user.id).first() is None:
                session.add(User(id = interaction.user.id))
                session.commit()

            result = session.query(SteamUser).where(SteamUser.id == interaction.user.id)
            if result.first():
                await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
                return
            session.add(SteamUser(id = interaction.user.id))
            session.commit()
        _, sub_mention = await self.act.get_app_sub_command(self.slash_show)
        await interaction.response.send_message(f"I will notify you of new steam games!\nUse {sub_mention} to view current sales.", ephemeral=True)


    @app_commands.command(name="remove", description="No longer get notified of free steam games")
    async def slash_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.query(SteamUser).where(SteamUser.id == interaction.user.id)
            user = result.first()
            if not user:
                await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
                return
            session.delete(user)
            session.commit()
        await interaction.response.send_message("I not notify you of new free steam games anymore.", ephemeral=True)


    # @app_commands.checks.cooldown(1, UPDATE_PERIOD)
    @app_commands.command(name="show", description="Get a list of steam games that are on sale for the given percentage or higher")
    async def slash_show(self, interaction: discord.Interaction, percent: int = 100,) -> None:
        await interaction.response.defer()

        embed = discord.Embed(title="Steam Games", description=f"Steam Games with sales {percent}% or higher", color=0x094d7f)
        embed = self.populate_embed(embed, self.get_steam_sales(percent))
        self.logger.debug(f"{embed.to_dict()}")

        if len(embed.fields) > 0:
            # await interaction.response.send_message(embed=embed, ephemeral=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # await interaction.response.send_message(f"No steam games found with {percent} or higher sales.", ephemeral=True)
            await interaction.followup.send(f"No steam games found with {percent} or higher sales.", ephemeral=True)


    async def cog_load(self) -> None:
        self.update.start()


    @tasks.loop(seconds=UPDATE_PERIOD)
    async def update(self) -> None:
        """
        creates a discord Embed object to send and notify users of new 100% sales.
        Expected amount of sales should be low enough it'll never reach embed size limit
        """
        self.logger.info("updating sales")

        embed = discord.Embed(title="Free Steam Game's", description="New free Steam Games have been found!", color=0x094d7f)
        new_sales = self.get_new_steam_sales(percent=100)
        self.logger.debug(f"{new_sales=}")
        embed = self.populate_embed(embed, new_sales)

        if embed is None:
            self.logger.warning("Got no populated embed, skipping sale sending.")
            return

        _, sub_mention_remove = await self.act.get_app_sub_command(self.slash_remove)
        _, sub_mention_show = await self.act.get_app_sub_command(self.slash_show)
        disable_message = f"You can disable this message by using {sub_mention_remove}"
        all_sale_message = f"You can see other sales by using {sub_mention_show}, followed by a percentage"

        with Session(engine) as session:
            users = session.query(SteamUser).all()
            self.logger.debug(f"Got embed with sales, {embed}, to send to {users=}")

            for db_user in users:
                self.logger.debug(f"Trying to show new sales to {db_user.id=}")
                try:    
                    user = self.bot.get_user(db_user.id) or await self.bot.fetch_user(db_user.id)
                except discord.errors.NotFound:
                    self.logger.warning(f"Not showing {db_user.id=} sales, discord.errors.NotFound")
                    continue
                dm = user.dm_channel or await user.create_dm()

                if len(embed.fields) > 0:
                    self.logger.debug(f"Showing {user}, {embed}")
                    await dm.send(content=f"{disable_message}\n{all_sale_message}", embed=embed)
                else:
                    self.logger.debug(f"Not showing sales, empty embed fields: {user}, {embed}")


    @update.before_loop
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    def populate_embed(self, embed: discord.Embed, sales: list[Sale]) -> discord.Embed:
        """Fills a given embed with sales, and then returns the populated embed

        Args:
            sales (list): List of found sales
            embed (discord.Embed): discord.Embed

        Returns:
            discord.Embed
        """
        if sales is None:
            return embed

        try:
            # Sort on sale percentage (int), so reverse to get highest first
            sales.sort(key=lambda x: x["sale_percent"], reverse=True)
        except AttributeError:
            pass

        for sale in sales:
            # install_game_uri = f"steam://install/{game_id}"
            embed_text = f"""
                Url: {sale["url"]}
                Sale: {sale["sale_percent"]}%
                Price {sale["final_price"]}
                Is dlc: {sale["is_dlc"]}
                Is bundle: {sale["is_bundle"]}
                Last Checked: {sale["update_datetime"].strftime(DATE_FORMAT)}
            """
            embed.add_field(
                name = sale["title"],
                value = dedent(embed_text),
                inline = False
            )
            self.logger.debug(f"Populated embed with:\n{sale=}")

        # embed size above 6000 characters.
        while len(str(embed.to_dict())) >= 6000:
            self.logger.debug(f"{len(str(embed.to_dict()))=}")
            self.logger.debug(f"removing to decrease size: {embed.fields[-1]=}")
            embed.remove_field(-1)
        
        self.logger.debug(f"Returning {embed}")
        return embed


    def get_updated_sales(self, sales: list[SteamSale | Sale]) -> list[Sale]:
        # sourcery skip: assign-if-exp, reintroduce-else
        """Return a new list of sales, based of a given list of sales

        Args:
            sales (list[SteamSale]): Old list to run checks on

        Returns:
            list[SteamSale]: New list that gets returned
        """
        # convert to Sale for each element that is SteamSale
        sales: list[Sale] = [
            self.db_to_dict(i)
            if isinstance(i, SteamSale)
            else i
            for i in sales
        ]

        updated_sales: list[Sale] = []
        for sale in sales:
            if self.is_outdated(sale):
                updated_sales.append(self.get_game_sale(sale["url"]))
            else:
                updated_sales.append(sale)

        self.logger.debug(f"{updated_sales=}")
        if sales == updated_sales:
            return sales
        return updated_sales


    @overload
    def is_outdated(self, sale: SteamSale) -> bool: ...
    @overload
    def is_outdated(self, sale: Sale) -> bool: ...
    def is_outdated(self, sale: SteamSale | Sale) -> bool:
        """Check if a sale has recently been updated

        Args:
            sale (SteamSale | Sale): The sale to check against

        Returns:
            bool: True, False
        """
        if isinstance(sale, SteamSale): # type: ignore
            update_period_date = sale.update_datetime + datetime.timedelta(minutes=UPDATE_PERIOD)
        else:
            update_period_date = sale["update_datetime"] + datetime.timedelta(minutes=UPDATE_PERIOD)

        return (
            update_period_date
            <= datetime.datetime.now()
        )


    def get_saved_sales(self, percent: int) -> list[SteamSale]:
        """get saved/known sales from database

        Returns:
            list[SteamSale]: List of SteamSale database objects
        """
        with Session(engine) as session:
            sales = session.query(SteamSale).where(SteamSale.sale_percent >= percent).all()
        self.logger.debug(f"saved {sales=}")
        return sales


    def get_id_from_game_url(self, url: str) -> int:
        """Get an id from a steam game url

        Args:
            url (str): Url to extract the id from

        Returns:
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
        """Find out if a url is for a bundle

        Args:
            url (str): Url to look through

        Returns:
            bool: True, False
        """
        # sourcery skip: class-extract-method
        # example: https://store.steampowered.com/bundle/23756/Bundle_with_fun_games/?l=dutch&curator_clanid=4777282
        regex_bundle = r"(?:https?:\/\/)?store\.steampowered\.com\/(bundle)\/\d+\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_bundle, url)
        self.logger.debug(f"bundle: {matches=}")
        return bool(matches)


    def is_valid_game_url(self, url: str) -> bool:
        """Find out if a url is for a valid game

        Args:
            url (str): Url to check for

        Returns:
            bool: True, False
        """
        return bool(self.get_id_from_game_url(url))


    def get_new_steam_sales(self, percent: int) -> list[Sale]:
        """Get only unknown/new sales

        Args:
            percent (int): Percentage to check for

        Returns:
            list[Sale]: List of TypedDict Sale
        """
        known_sales = [self.db_to_dict(i) for i in self.get_saved_sales(percent)]
        steam_sales = self.get_sales_from_steam(percent)
        
        self.logger.debug(f"checking for new sales, \n{known_sales=}, \n{steam_sales=}")

        outdated = [
            i["title"]
            for i in known_sales
            if self.is_outdated(i)
        ]

        return [
            sale
            for sale in steam_sales
            if sale["title"] not in outdated
        ]


    def get_steam_sales(self, percent: int) -> list[Sale]:
        """get sales from database or from website depending on `UPDATE_PERIOD`

        Returns:
            list[SteamSale]: List of SteamSale database objects
        """
        # return self.get_updated_sales(self.get_saved_sales(percent)) or self.get_sales_from_steam(percent)

        updated_sales = self.get_updated_sales(self.get_saved_sales(percent))
        if updated_sales == []:
            self.logger.debug("getting sales from steam")
            return self.get_sales_from_steam(percent)
        else:
            self.logger.debug("returning known sales")
            return updated_sales


    def get_games_from_bundle(self, url: str) -> list[Sale]:
        """Get the sales from a bundle

        Args:
            url (str): Url of the bundle to get the game sales from

        Raises:
            ValueError: Error when url is invalid

        Returns:
            SteamSale: SteamSale database object
        """
        if not self.is_bundle(url):
            raise ValueError("Invalid Steam Bundle URL")

        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")

        game_sales = []
        for sale_tag in soup.find_all("a", class_=BUNDLE_LINK):
            sale_tag: bs4.element.Tag
            game_sales.append(self.get_game_sale(sale_tag["href"]))
        return game_sales


    def db_to_dict(self, sale: SteamSale) -> Sale:
        """Convert a SteamSale db object to TypedDict Sale

        Args:
            sale (SteamSale): SteamSale database object

        Returns:
            Sale: TypedDict containing the same items as Db object
        """
        return {
            "title": sale.title,
            "url": sale.url,
            "sale_percent": sale.sale_percent,
            "final_price": sale.final_price,
            "is_dlc": sale.is_dlc,
            "is_bundle": sale.is_bundle,
            "update_datetime": sale.update_datetime
        }


    def get_sales_from_steam(self, percent: int) -> list[Sale]:
        """Scrape sales from https://store.steampowered.com/search/
        With the search options: Ascending price, Special deals, English

        Args:
            search_percent (int, optional): Percentage of sale to look for. Defaults to 100.

        Returns:
            list[Sale]: List of SteamSale database objects
        """
        html = requests.get(config["Steam"]["url"]).text
        soup = BeautifulSoup(html, "html.parser")
        sales: list[Sale] = []
        with Session(engine) as session:
            for sale_tag in soup.find_all(class_=DISCOUNT_PERCENT):
                sale_tag: bs4.element.Tag
                # strip the - and % from the tag
                discount = int(sale_tag.text[1:-1])
                sale = sale_tag.find_parent("a")

                if sale is None:
                    self.logger.warning(f"Got empty sale: {sale_tag=}, {sale=}")

                if discount >= percent:
                    price = sale.find(class_=DISCOUNT_FINAL_PRICE).text[:-1].replace(",", ".")
                    sale = SteamSale(
                        id = sale[DATA_APPID],
                        title = sale.find(class_=SEARCH_GAME_TITLE).text,
                        url = sale["href"],
                        sale_percent = discount,
                        final_price = float(price), # strip €. TODO: might cause bugs when it isn't shown as €
                        is_dlc = False,
                        is_bundle = False,
                        update_datetime = datetime.datetime.now(),
                    )
                    sales.append(self.add_sale(session, sale, "steam search"))

            session.commit()

        return sales


    def get_bundle_sale(self, url: str) -> Sale:
        # sourcery skip: extract-method
        """Get sale for a bundle

        Args:
            url (str): Url of the bundle to get the sale from

        Raises:
            ValueError: Error when url is invalid

        Returns:
            SteamSale: SteamSale database object
        """
        if not self.is_bundle(url):
            raise ValueError("Invalid Steam Bundle URL")

        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")

        with Session(engine) as session:
            price = soup.find(class_=BUNDLE_FINAL_PRICE).text[:-1].replace(",", ".")
            sale = SteamSale(
                id = self.get_id_from_game_url(url),
                title = soup.find(class_=BUNDLE_TITLE).text,
                url = url,
                sale_percent = soup.find(class_=BUNDLE_DISCOUNT).text[:-1], # strip %
                final_price = float(price), # strip €. TODO: might cause bugs when it isn't shown as €
                is_dlc = False,
                is_bundle = True,
                update_datetime = datetime.datetime.now(),
            )
            return self.add_sale(session, sale, "bundle")


    def get_game_sale(self, url: str) -> Sale:
        # sourcery skip: extract-method
        """get a single game sale from specific url

        Args:
            url (str): Url of the game to get a sale from

        Raises:
            ValueError: Error when url is invalid

        Returns:
            SteamSale: SteamSale database object
        """
        if not self.is_valid_game_url(url):
            raise ValueError("Invalid Steam Game URL")

        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")
        regex = r"btn_add_to_cart_\d+"

        title = soup.find(class_=SINGLE_GAME_TITLE).text
        add_to_cart = soup.find("a", href=re.compile(regex))
        buy_area = add_to_cart.find_parent(class_=GAME_BUY_AREA)

        with Session(engine) as session:
            price = buy_area.find(class_=DISCOUNT_FINAL_PRICE).text[:-1].replace(",", ".")
            sale = SteamSale(
                id = self.get_id_from_game_url(url),
                title = title,
                url = sale["href"],
                sale_percent = buy_area.find(class_=DISCOUNT_PERCENT).text[1:-1], # strip - and % from sale tag
                final_price = float(price), # strip €. TODO: might cause bugs when it isn't shown as €
                is_dlc = (buy_area.find(class_=GAME_RELEVANT).text == IS_DLC_RELEVANT_TO_YOU), # boolean, match 2 texts to check dlc
                is_bundle = False,
                update_datetime = datetime.datetime.now(),
            )
            return self.add_sale(session, sale, "game")


    def update_sale(self, session: Session, sale: SteamSale) -> bool:
        """Update a sale record in Database, if successful return True

        Args:
            session (Session): Session to connect to DataBase
            sale (SteamSale): Sale to update

        Returns:
            bool: True, False
        """
        if known:= session.query(SteamSale).where(SteamSale.id == sale.id).first():
            known.title = sale.title
            known.url = sale.url
            known.sale_percent = sale.sale_percent
            known.final_price = sale.final_price
            known.is_dlc = sale.is_dlc
            known.is_bundle = sale.is_bundle
            known.update_datetime = sale.update_datetime
            return True
        return False


    def add_sale(self, session: Session, sale: SteamSale, category: str) -> Sale:
        """Add a sale to db, and return presentable TypedDict

        Args:
            session (Session): Session for database connection
            sale (SteamSale): SteamSale database object
            category (str): Category where sale was found

        Returns:
            Sale: TypedDict in presentable format
        """
        if not self.update_sale(session, sale):
            session.add(sale)
        session.commit()
        self.logger.debug(f"Found {category} {sale=}")
        return self.db_to_dict(sale)


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Steam(bot))
