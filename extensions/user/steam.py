import datetime
import logging
import os
import random
import re
from typing import Any, Optional, TypedDict

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks

import rainbow
from tools import app_command_tools
from tools.config_reader import config
from tools.database_tables import Session
from tools.database_tables import Steam as SteamDb
from tools.database_tables import User, engine


# Set update period and cooldown for user command.
UPDATE_PERIOD = 3600 * 3 # 3 hour cooldown
HTML_SIZE_LIMIT = 50_000_000
ENCODING = "utf-8"


class Sale(TypedDict):
    title: str
    sale_amount: int
    url: str
    is_dlc: bool


class Steam(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.base_path = "./database/steam"
        self.sales_file = f"{self.base_path}/SteamPage.html"
        self.sales_backup_file = f"{self.base_path}/SteamPageBackup.html"
        self.known_sales = []
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.setup_html_files()
        self.act = app_command_tools.Converter(bot=self.bot)


    async def cog_load(self) -> None:
        self.update.start()


    def setup_html_files(self) -> None:
        os.makedirs(self.base_path, exist_ok=True)
        if not os.path.exists(self.sales_file):
            with open(self.sales_file, "w") as f:
                f.write("")
                f.close()
            self.logger.info("Empty Steam Html created")
        else:
            self.logger.info("Steam local Html exists")

        if not os.path.exists(self.sales_backup_file):
            with open(self.sales_backup_file, "w") as f:
                f.write("")
                f.close()
            self.logger.info("Empty Steam Html backup created")
        else:
            self.logger.info("Steam local Html backup exists")


    def check_empty(self, path: str) -> bool:
        if os.path.exists(path):
            with open(path, "r", encoding=ENCODING) as f:
                return f.read() == ""
        return True


    async def _get_saved_html(self, url: str, file: str) -> str:
        """Handles everything related to fetching and updating the steam page either from url,
        or from a saved html file

        Returns:
            str: returns the html as a str
        """
        # sourcery skip: aware-datetime-for-utc
        self.logger.debug(f"getting html {file=}")
        if not self.check_empty(file):
            self.logger.debug("htmlFile not empty")
            diff = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(file))
            self.logger.debug(f"{diff=}")
            if diff < datetime.timedelta(seconds=UPDATE_PERIOD):
                return await self._get_html_from_saved(file)
        return await self._get_html_from_url(url=url, file=file)


    async def _get_game_html(self, game_id) -> str:
        """Handles everything related to fetching and updating the game page either from url,
        or from a saved html file

        Returns:
            str: returns the html as a str
        """
        self.logger.debug(f"getting html for {game_id=}")
        game_url = f"https://store.steampowered.com/app/{game_id}"
        return await self._get_saved_html(url=game_url, file=f"{self.base_path}/{game_id}.html")


    async def get_game_sale(self, game_id: int) -> Sale:
        """Get a Sale from a game id on Steam

        Args:
            game_id (int): Id to check

        Returns:
            Sale: Dictionary containing title, sale amount, url and is_dlc
        """
        # TODO: add func call somewhere else and find out when to use this.
        html = await self._get_game_html(game_id)

        soup = BeautifulSoup(html, "html.parser")
        sale_amount = soup.find(class_="discount_pct") # type: ignore
        game_meta = soup.find(class_="rightcol game_meta_data")
        dlc = game_meta.find(class_="block responsive_apppage_details_right heading responsive_hidden")
        title = soup.find(class_="apphub_AppName")
        is_dlc = dlc.text == "Is this DLC relevant to you?"

        url = f"https://store.steampowered.com/app/{game_id}"
        sale = {
            "title": title.text,
            "sale_amount": int(sale_amount.text[1:-1]), # strip the - and % from sale_amount.text
            "url": url,
            "is_dlc": is_dlc
        }

        self.logger.debug(sale)
        return sale


    async def _get_html_from_url(self, url: str, file: str = None) -> str:
        r = requests.get(url)
        self.logger.debug("Returning Steam html from url")

        await self._save_html_file(file, r)
        return r.text


    async def _save_html_file(self, file: str, r: requests.Response) -> None:
        if file is None:
            self.logger.warning("no file to safe to")
            return

        self.logger.debug(f"Updating {file=}")
        with open(file, "w", encoding=ENCODING) as f:
            f.write(r.text)


    async def _get_html_from_saved(self, file) -> str:
        self.logger.debug(f"Returning {file=}")
        with open(self.sales_file, "r", encoding=ENCODING) as f:
            self.logger.debug("Returning Steam html from saved file")
            return f.read()


    def is_bundle(self, url: str) -> bool:
        self.logger.debug(f"Checking bundle: {url}")
        regex_bundle = r"(?:https?:\/\/)?store\.steampowered\.com\/(bundle)\/(?:\d+)\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_bundle, url)
        return len(matches) >= 1


    async def sales_from_html(self, html: str) -> list[Sale]:
        sales: list[Sale] = []
        soup = BeautifulSoup(html, "html.parser")
        # for i in soup.find_all(class_="col search_discount responsive_secondrow"):
        for i in soup.find_all("span", {"class": "title"}):
            i: BeautifulSoup # works for highlighting i.parent, and i.find
            steam_item: BeautifulSoup = i.parent.parent.parent # go to <a> tag, from title.

            url = steam_item["href"]
            if self.is_bundle(url):
                self.logger.debug(f"skipping bundle: {url}")
                continue

            title = i.text
            sale_amount = steam_item.find(class_="discount_pct")
            try:
                sale: Sale = {
                    "title": title,
                    "sale_amount": int(sale_amount.text[1:-1]), # strip the - and % from sale_amount.text
                    "url": url,
                    "is_dlc": None,
                }
                # FIXME: always returns empty
                # game_id = self.get_game_id(sale)
                # game_sale = await self.get_game_sale(game_id)
                # sales.append(game_sale) 
                # self.logger.debug(f"{sale=}, {game_id=}, {game_sale=}")
                sales.append(sale)
            except AttributeError:
                # self.logger.exception(f"Skipping adding sale, Could not append: {e}")
                continue
        self.logger.debug(f"Returning sales {sales}")
        return sales


    def is_dupe(self, *to_check: Any) -> bool:
        self.logger.debug(f"dupe checking {to_check}")
        seen = []
        for i in to_check:
            if i not in seen:
                seen.append(i)
            else:
                break
        else:
            return True
        return False


    def find_percentage_sales(self, sales: list[Sale], percentage: int) -> list[Sale]:
        requested_sales: list[Sale] = []
        for perc in range(percentage, 101):
            # format: i[title, sale_amount, url]
            target_sales: Sale = [
                i
                for i in sales
                if i["sale_amount"] == perc
            ]
            requested_sales.extend(target_sales)
            self.logger.debug(f"found {perc} sale, {target_sales}")
        self.logger.debug(f"returning {requested_sales=}")
        return requested_sales


    def get_game_id(self, sale: Sale) -> int:
        regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"
        matches = re.findall(regex_game_id, sale["url"])
        try:
            return int(matches[0])
        except IndexError as e:
            self.logger.warning(f"Game_id not found: {e}, {sale}")


    async def populate_embed(self, sales: list[Sale], embed: discord.Embed) -> Optional[discord.Embed]:
        """Fills an embed with sales, and then returns the populated embed

        Args:
            sales (list): List of found sales
            embed (discord.Embed): discord.Embed

        Returns:
            discord.Embed
        """
        if sales is None:
            return

        # Switch to following regex?
        # r"^https:\/\/store\.steampowered\.com\/app\/(\d+)\/?.*$"gm

        try:
            # Sort on int, so reverse to get highest first
            sales.sort(key=lambda x: x["sale_amount"], reverse=True)
        except AttributeError:
            pass

        for sale in sales:
            # game: Sale = {"title":i[0], "sale_amount":i[1], "url":i[2]}
            game_id = self.get_game_id(sale)

            match sale["is_dlc"]:
                case True:
                    is_dlc = "yes"
                case False:
                    is_dlc = "no"
                case None:
                    is_dlc = "unknown"

            # install_game_uri = f"steam://install/{game_id}"
            embed.add_field(name=sale["title"], value=f"{sale['url']}\nSale: {sale['sale_amount']}%\nDlc: {is_dlc}", inline=False)
            # rungameid doesn't work with new discord custom url [text](https://link.url)
            # run_game_id = f"steam://rungameid/{game_id}"
            # \nInstall directly here: {install_game_uri}

            self.logger.debug(f"Populate embed with:\nSale: {sale}\nGameId: {game_id}")
        self.logger.debug("Returning filled embed")
        return embed


    def get_new_freebies(self, old: list[Sale], new: list[Sale]) -> Optional[list[Sale]]:
        """Check if sale's from NEW are not found in OLD


        Args:
            old (List): Old Sales list to check against
            new (List): New Sales list to check from


        Returns:
            new_sales (List): List of new sales
        """
        self.logger.debug(f"Checking for new item(s): {old=}, {new=}")
        new_sales = [
            sale
            for sale in new
            if sale not in old
            and sale["sale_amount"] == 100
        ]
        if not new_sales:
            self.logger.info("No new sale from_html")
            return None
        return new_sales


    def saved_file_size_check(self, size_in_kb: int) -> bool:
        total_size = sum(
            os.path.getsize(os.path.join(root, file))
            for root, _, files in os.walk(self.base_path)
            for file in files
        )
        self.logger.debug(f"{total_size=} {size_in_kb=}")
        return total_size > size_in_kb


    def remove_oldest_html_file(self) -> None:
        oldest_files = sorted((
                os.path.join(root, file)
                for root, _, files in os.walk(self.base_path)
                for file in files
            ),
            key=os.path.getctime,
        )
        self.logger.info(f"deleting old html for space: {oldest_files[0]=}")

        os.remove(oldest_files[0])


    @tasks.loop(seconds=UPDATE_PERIOD)
    async def update(self) -> None:
        """
        Check if the sales from Html request and Html file are the same
        When they are not, replaces old .html with the latest one
        and creates a discord Embed object to send and notify users.
        Expected amount of sales should be low enough it'll never reach embed size limit
        """
        while self.saved_file_size_check(HTML_SIZE_LIMIT):
            self.remove_oldest_html_file()

        self.logger.info("Checking for sales.")
        html = await self._get_saved_html(config["Steam"]["url"], self.sales_file)

        with open(self.sales_backup_file, "r", encoding=ENCODING) as f:
            file_sales = await self.sales_from_html(f.read())

        html_sales = await self.sales_from_html(html)
        if self.is_dupe(html_sales, file_sales):
            return None

        embed = discord.Embed(title="Free Steam Game's", description="New free Steam Games have been found!", color=random.choice(rainbow.RAINBOW))
        new_sales = self.get_new_freebies(file_sales, html_sales)

        if new_sales is None:
            self.logger.debug("No sale, skipping sale sending.")
            return 

        embed = await self.populate_embed(new_sales, embed)

        if embed is None:
            self.logger.warning("Got no populated embed, skipping sale sending.")
            return

        _, sub_mention_remove = await self.act.get_app_sub_command(self.slash_remove)
        _, sub_mention_show = await self.act.get_app_sub_command(self.slash_show)
        disable_message = f"You can disable this message by using {sub_mention_remove}"
        all_sale_message = f"You can see other sales by using {sub_mention_show}"

        with Session(engine) as session:
            users = session.query(SteamDb).all()
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

        self.logger.debug(f"Updating {self.sales_backup_file=}")
        with open(self.sales_backup_file, "w", encoding=ENCODING) as f:
            f.write(html)
            f.close()


    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @app_commands.checks.cooldown(1, UPDATE_PERIOD)
    @app_commands.command(name = "show", description = "Get a list of steam games that are on sale for the given percentage or higher")
    async def slash_show(self, interaction: discord.Interaction, percent: int = 100,) -> None:
        await interaction.response.defer()
        html = await self._get_saved_html(config["Steam"]["url"], self.sales_file)
        html_sales = await self.sales_from_html(html)
        target_sales = self.find_percentage_sales(html_sales, percent)
        # self.is_dupe(html_sales, html_sales)

        embed=discord.Embed(title="Steam Games", description=f"Steam Games with sales {percent} or higher", color=0x094d7f)
        embed = await self.populate_embed(target_sales, embed)

        if len(embed.fields) > 0:
            # await interaction.response.send_message(embed=embed, ephemeral=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # await interaction.response.send_message(f"No steam games found with {percent} or higher sales.", ephemeral=True)
            await interaction.followup.send(f"No steam games found with {percent} or higher sales.", ephemeral=True)


    @app_commands.command(name = "add", description = "Get notified automatically about free steam games")
    async def slash_add(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            if session.query(User).where(User.id == interaction.user.id).first() is None:
                session.add(User(id = interaction.user.id))
                session.commit()

            result = session.query(SteamDb).where(SteamDb.id == interaction.user.id)
            if result.first():
                await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
                return
            session.add(SteamDb(id = interaction.user.id))
            session.commit()
        _, sub_mention = await self.act.get_app_sub_command(self.slash_show)
        await interaction.response.send_message(f"I will notify you of new steam games!\nUse {sub_mention} to view current sales.", ephemeral=True)


    @app_commands.command(name = "remove", description = "No longer get notified of free steam games")
    async def slash_remove(self, interaction:discord.Interaction) -> None:
        with Session(engine) as session:
            result = session.query(SteamDb).where(SteamDb.id == interaction.user.id)
            user = result.first()
            if not user:
                await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
                return
            session.delete(user)
            session.commit()
        await interaction.response.send_message("I not notify you of new free steam games anymore.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Steam(bot))
