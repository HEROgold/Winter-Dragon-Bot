import pickle
import logging
import os
import random
import re

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks

import config
import dragon_database
import rainbow

class Steam(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.htmlFile = '.\\Database/SteamPage.html'
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        self.setup_html_file()
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                pickle.dump(self.data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def setup_html_file(self) -> None:
        if not os.path.exists(self.htmlFile):
            with open(self.htmlFile, "w") as f:
                f.write("")
                f.close()
            self.logger.info("Empty Steam Html created")
        else:
            self.logger.info("Steam local Html exists")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = await self.get_data()
        if not self.data:
            self.data = {"user_id":[]}
        self.update.start()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    async def get_html(self, url=config.Steam.URL) -> str:
        requests.get(url)
        r = requests.get(url)
        self.logger.debug("Returning Steam html from url")
        return r.text

    async def sale_from_html(self, html:str) -> list:
        sales = []
        soup = BeautifulSoup(html, "html.parser")
        for i in soup.find_all(class_="col search_discount responsive_secondrow"):
            i:BeautifulSoup
            item:BeautifulSoup = i.parent.parent.parent
            url = item["href"]
            title = item.find("span", {"class": "title"})
            sale_amount = i.find("span") or sale_amount["text":"-1000%!"]
            try:
                sales.append([title.text, sale_amount.text, url])
            except Exception as e:
                self.logger.exception(f"Could not append: {e}")
                continue
        return sales

    async def dupe_check(self, html:str, html_file_path:str) -> bool:
        from_file = await self.sale_from_file(html_file_path)
        from_html = await self.sale_from_html(html)
        a_hundred, b_hundred = self.find_100_sales(from_file, from_html)
        if from_file == []:
            self.logger.debug("Copied SteamPage.html is empty.")
            return False
        if from_html == from_file:
            self.logger.debug("Steam File and Html are the same, not checking new sales")
            return True
        elif a_hundred == b_hundred:
            self.logger.debug("Sales from File and Html are the same, not checking new sales.")
            return True
        else:
            self.logger.debug("Steam File and Html not the same. Checking for new sales.")
            return await self.check_new(a_hundred, b_hundred)

    async def sale_from_file(self, html_file_path) -> list:
        with open(html_file_path, "r", encoding="utf-8") as f:
            from_file = await self.sale_from_html(f.read())
        return from_file

    def find_100_sales(self, from_file:list, from_html:list) -> tuple[list, list]:
        a = []
        b = []
        for i,j in zip(from_file, from_html):
            # Keep both lists same size!
            if i[1] == "-100%" or j[1] == "-100%":
                a.append(i)
                b.append(j)
        a.sort()
        b.sort()
        self.logger.debug(f"SteamLists: \n{a}, \n{b}")
        return a, b

    async def check_new(self, from_file:list[list], from_html:list[list]) -> bool:
        """Check if sale from html is not found inside the saved html file

        Args:
            from_file (List): Sales from saved file
            from_html (List): Sales from requested url

        Returns:
            bool: True when new sale is found, false on loop ending
        """
        self.logger.debug(f"Checking for new item(s): a={from_file} b={from_html}")
        for sale in from_html:
            if sale not in from_file and sale[1] == "-100%":
                self.logger.info(f"New sale found from_html: {sale}")
                return True
        self.logger.info(f"No new sale found from_html: {sale}")
        return False

    @tasks.loop(seconds=21600) # 6 hours > 21600
    async def update(self) -> None:
        """
        Check if the sales from Html request and Html file are the same

        When they are not, replaces old .html with the latest one
        and creates a discord Embed object to send and notify users.
        """
        html = await self.get_html()
        dupe = await self.dupe_check(html, self.htmlFile)
        if dupe == True:
            return None
        with open(self.htmlFile, "w", encoding="utf-8") as f:
            f.write(html)
            f.close()
        sales_html = await self.sale_from_html(html)
        embed = discord.Embed(title="Free Steam Game's", description="New free Steam Games have been found!", color=random.choice(rainbow.RAINBOW))
        embed.set_footer(text="You can disable this by using `/steam remove `")
        embed = await self.populate_embed(sales_html, embed)
        for id in self.data["user_id"]:
            user = self.bot.get_user(int(id))
            dm = user.dm_channel or await user.create_dm()
            self.logger.debug(f"Showing {user}, {embed}")
            if len(embed.fields) > 0:
                await dm.send(embed=embed)

    async def populate_embed(self, sales:list, embed:discord.Embed) -> discord.Embed:
        """Fills an embed with sales, and then returns the populated embed

        Args:
            sales (list): List of found sales
            embed (discord.Embed): discord.Embed

        Returns:
            discord.Embed
        """
        for i in sales:
            if i[1] == "-100%":
                game_title = i[0]
                game_url = i[2]
                regex_game_id = r"(?:https?:\/\/)?store\.steampowered\.com\/app\/(\d+)\/[a-zA-Z0-9_\/]+"
                game_id = re.findall(regex_game_id, game_url)
                # TODO: Check this on next sale!
                # 'https://store.steampowered.com/app/2279791/Forspoken_Cats_Meow_Cloak/?snr=1_7_7_2300_150_1'
                # https://store.steampowered.com/
                # then add steam://rungameid/2279791
                run_game_id = f"steam://rungameid/{game_id[0] or game_id}"
                embed.add_field(name=game_title, value=f"{game_url}\nInstall here: {run_game_id}", inline=False)
                self.logger.debug(f"Pupulate embed with:\nSale: {i}\nGameId: {game_id}")
        return embed

    @app_commands.command(name = "show", description= "Get a list of 100% Sale steam games.")
    @app_commands.checks.cooldown(1, 300)
    async def slash_show(self, interaction: discord.Interaction) -> None:
        html = await self.get_html()
        sales_html = await self.sale_from_html(html)
        embed=discord.Embed(title="Free Steam Game", description="Free Steam Games!", color=0x094d7f)
        embed = await self.populate_embed(sales_html, embed)
        if len(embed.fields) != 0:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No free steam games found.")

    @app_commands.command(name = "remove", description = "No longer get notified of free steam games")
    async def slash_remove(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = await self.get_data()
        id_list = self.data["user_id"]
        if interaction.user.id in id_list:
            id_list.remove(interaction.user.id)
            await interaction.response.send_message("I not notify you of new steam games anymore.", ephemeral=True)
        else:
            await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
        await self.set_data(self.data)

    @app_commands.command(name = "add", description = "Get notified automatically about free steam games")
    async def slash_add(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = await self.get_data()
        id_list = self.data["user_id"]
        if interaction.user.id not in id_list:
            id_list.append(interaction.user.id)
            await interaction.response.send_message("I will notify you of new steam games!", ephemeral=True)
        else:
            await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
        await self.set_data(self.data)

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Steam(bot))
