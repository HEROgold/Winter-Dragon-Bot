import asyncio
import json
import logging
import os
import random

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

import config
import dragon_database
import config
import rainbow

class Steam(commands.GroupCog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "SteamMention"
        self.htmlFile = '.\\Database/SteamPage.html'
        self.logger = logging.getLogger("winter_dragon.steam")
        self.setup_html()
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.database_name}.json"
            self.setup_json()

    def setup_json(self):
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {"user_id" : []}
                json.dump(data, f)
                f.close
                self.logger.debug(f"{self.database_name} Json Created.")
        else:
            self.logger.debug(f"{self.database_name} Json Loaded.")

    def setup_html(self):
        if not os.path.exists(self.htmlFile):
            with open(self.htmlFile, "w") as f:
                f.write("")
                f.close()
            self.logger.debug("Empty Steam Html created")
        else:
            self.logger.debug("Steam Html found")

    async def get_data(self) -> dict[str, list]:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update()

    async def get_html(self, url=config.Steam.URL) -> str:
        requests.get(url)
        r = requests.get(url)
        self.logger.debug("returning steam page")
        return r.text

    async def sale_from_html(self, html) -> list:
        sales = []
        soup = BeautifulSoup(html, "html.parser")
        for i in soup.find_all(class_="col search_discount responsive_secondrow"):
            item = i.parent.parent.parent
            url = item["href"]
            title = item.find("span", {"class": "title"})
            sale = i.find("span")
            try:
                sales.append([title.text, sale.text, url])
            except Exception as e:
                self.logger.exception("Could not append:", e)
        return sales

    async def dupe_check(self, html:str, html_file_path:str) -> bool:
        from_file = await self.sale_from_file(html_file_path)
        from_html = await self.sale_from_html(html)
        a_hundred, b_hundred = self.find_100_sales(from_file, from_html)
        if from_file == []:
            self.logger.debug("Copied SteamPage.html is empty")
            return False
        if from_html == from_file:
            self.logger.debug("Steam File and Html are the same.")
            return True
        elif a_hundred == b_hundred:
            self.logger.debug("Sales from File and Html are the same")
            return True
        else:
            self.logger.debug("Steam File and Html are not the same.")
            return await self.check_new(a_hundred, b_hundred)

    async def sale_from_file(self, html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            from_file = await self.sale_from_html(f.read())
        return from_file

    def find_100_sales(self, from_file, from_html) -> list[list]:
        a = []
        b = []
        try:
            for i,j in zip(from_file, from_html):
                # Keep both lists same size!
                if i[1] == "-100%" or j[1] == "-100%":
                    a.append(i)
                    b.append(j)
        except Exception as e:
            self.logger.exception(e)
        a.sort()
        b.sort()
        self.logger.debug(f"SteamLists: {a}, {b}")
        return a, b

    async def check_new(self, from_file:list[list], from_html:list[list]) -> bool:
        self.logger.debug(f"Checking for new item(s): a={from_file} b={from_html}")
        for sale in from_html:
            if sale not in from_file and sale[1] == "-100%":
                self.logger.debug(f"new from_html: {sale}")
                return True
        return False

    async def update(self) -> None:
        """
        Check if the sales from Html request and Html file are the same

        When they are not, replaces old .html with the latest one
        and creates a discord Embed object to send and notify users.

        WARNING this uses a timer and loops itself every so often!
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
        embed.set_footer(text="You can disable this by using `/remove_free_steam`")
        embed = await self.populate_embed(sales_html, embed)
        data = await self.get_data()
        for id in data["user_id"]:
            user = self.bot.get_user(int(id))
            dm = await user.create_dm()
            if len(embed.fields) != 0:
                await dm.send(embed=embed)
        # timer to fight ratelimits and unnecessary checks in seconds
        # seconds > minutes > hours
        await asyncio.sleep(60*60*1)
        await self.update()

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
                name = i[0]
                field_val = i[2]
                embed.add_field(name=name, value=field_val, inline=False)
        return embed

    @app_commands.command(name = "show", description= "Get a list of 100% Sale steam games.")
    async def slash_show(self, interaction: discord.Interaction):
        html = await self.get_html()
        sales_html = await self.sale_from_html(html)
        embed=discord.Embed(title="Free Steam Game", description="Free Steam Games!", color=0x094d7f)
        embed = await self.populate_embed(sales_html, embed)
        if len(embed.fields) != 0:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No free steam games found.")

    @app_commands.command(name = "remove", description = "No longer get notified of free steam games")
    async def slash_remove(self, interaction:discord.Interaction):
        data = await self.get_data()
        id_list = data["user_id"]
        if interaction.user.id in id_list:
            id_list.remove(interaction.user.id)
            await interaction.response.send_message("I not notify you of new steam games anymore.", ephemeral=True)
        else:
            await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
        await self.set_data(data)

    @app_commands.command(name = "add", description = "Get notified automatically about free steam games")
    async def slash_add(self, interaction:discord.Interaction):
        data = await self.get_data()
        id_list = data["user_id"]
        if interaction.user.id not in id_list:
            id_list.append(interaction.user.id)
            await interaction.response.send_message("I will notify you of new steam games!", ephemeral=True)
        else:
            await interaction.response.send_message("Already in the list of recipients", ephemeral=True)
        await self.set_data(data)

async def setup(bot:commands.Bot):
    await bot.add_cog(Steam(bot))
