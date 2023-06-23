import logging
import os
import random
import re
from typing import Callable, Optional

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks

import config
import rainbow
from tools import app_command_tools
from tools.database_tables import Steam as SteamDb
from tools.database_tables import Session, engine, User


class Steam(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.htmlFile = './database/SteamPage.html'
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.setup_html_file()
        self.act = app_command_tools.Converter(bot=self.bot)


    async def cog_load(self) -> None:
        self.update.start()


    def setup_html_file(self) -> None:
        if not os.path.exists(self.htmlFile):
            with open(self.htmlFile, "w") as f:
                f.write("")
                f.close()
            self.logger.info("Empty Steam Html created")
        else:
            self.logger.info("Steam local Html exists")


    def get_html_from_url(self, url: str = config.Steam.URL) -> str:
        requests.get(url)
        r = requests.get(url)
        self.logger.debug("Returning Steam html from url")
        return r.text


    def sales_from_html(self, html: str) -> list[str]:
        sales = []
        soup = BeautifulSoup(html, "html.parser")
        for i in soup.find_all(class_="col search_discount responsive_secondrow"):
            i: BeautifulSoup
            steam_item: BeautifulSoup = i.parent.parent.parent
            url = steam_item["href"]
            title = steam_item.find("span", {"class": "title"})
            sale_amount = i.find("span")
            # self.logger.debug(f"{title, url, sale_amount}")
            try:
                sales.append([title.text, sale_amount.text, url])
            except AttributeError:
                # self.logger.exception(f"Skipping adding sale, Could not append: {e}")
                continue
        self.logger.debug(f"Returning sales {sales}")
        return sales


    def is_dupe(self, *to_check: list) -> bool:
        self.logger.debug(f"dupe checking {to_check}")
        first = to_check[0]
        for i in to_check:
            if i != first:
                break
        else:
            return True
        return False


    def find_percentage_sales(self, sales: list, percentage: int) -> list:
        requested_sales = []
        for perc in range(percentage, 101):
            sale_amount = fr"-{perc}%"
            # format: i[title, sale_amount, url]
            percent_sales = [i for i in sales if i[1] == sale_amount]
            requested_sales.extend(percent_sales)
            self.logger.debug(f"found {perc} sale, {percent_sales}")
        requested_sales.sort()
        self.logger.debug(f"returning {requested_sales=}")
        return requested_sales


    async def populate_embed(self, sales: list, embed: discord.Embed) -> discord.Embed:
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
        regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"

        try:
            sort_key: Callable[[str]] = lambda x: x[1]
            sales.sort(key=sort_key)
        except AttributeError:
            pass

        for i in sales:
            game_title = i[0]
            game_sale = i[1]
            game_url = i[2]
            game_id = re.findall(regex_game_id, game_url)
            try:
                game_id = game_id[0]
            except IndexError as e:
                self.logger.warning(f"Game_id not found: {e}, {i}")
                continue
            # rungameid doesn't work with new discord custom url [text](https://link.url)
            # run_game_id = f"steam://rungameid/{game_id}"
            install_game_id = f"steam://install/{game_id}"
            embed.add_field(name=game_title, value=f"{game_url}\nSale: {game_sale}\nInstall directly here: {install_game_id}", inline=False)
            self.logger.debug(f"Populate embed with:\nSale: {i}\nGameId: {game_id}")
        self.logger.debug("Returning filled embed")
        return embed


    def get_new_freebies(self, old: list[list], new: list[list]) -> Optional[list]:
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
            if sale not in old and sale[1] == "-100%"
        ]
        if not new_sales:
            self.logger.info("No new sale from_html")
            return None
        return new_sales


    @tasks.loop(seconds=3600) # 6 hours > 21600, default.
    async def update(self) -> None:
        """
        Check if the sales from Html request and Html file are the same
        When they are not, replaces old .html with the latest one
        and creates a discord Embed object to send and notify users.
        """
        self.logger.info("Checking for sales.")
        html = self.get_html_from_url()
        html_sales = self.sales_from_html(html)
        with open(self.htmlFile, "r", encoding="utf8") as f:
            file_sales = self.sales_from_html(f.read())


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

        self.logger.debug(f"Updating {self.htmlFile}")
        with open(self.htmlFile, "w", encoding="utf-8") as f:
            f.write(html)
            f.close()


    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @app_commands.checks.cooldown(1, 3600)
    @app_commands.command(name = "show", description = "Get a list of steam games that are on sale for the given percentage or higher")
    async def slash_show(self, interaction: discord.Interaction, percent: int = 100,) -> None:
        await interaction.response.defer()
        html = self.get_html_from_url()
        html_sales = self.sales_from_html(html)
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
