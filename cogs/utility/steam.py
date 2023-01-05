import asyncio
import json
import logging
import os

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

import config
import dragon_database
import config

class Steam(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.database_name = "SteamMention"
        self.htmlFile = '.\\Database/SteamPage.html'
        self.logger = logging.getLogger("winter_dragon.steam")
        self.setup_html()
        if not config.main.use_database:
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
        if config.main.use_database:
            db = dragon_database.Database()
            data = await db.get_data(self.database_name)
        else:
            with open(self.DBLocation, 'r') as f:
                data = json.load(f)
        return data

    async def set_data(self, data):
        if config.main.use_database:
            db = dragon_database.Database()
            await db.set_data(self.database_name, data=data)
        else:
            with open(self.DBLocation,'w') as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update()

    async def get_html(self, url=config.steam.url) -> str:
        requests.get(url)
        r = requests.get(url)
        return r.text

    async def find_free_sale(self, html) -> list:
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

    async def dupe_check(self, html:str, htmlFile:str) -> bool:
        # sourcery skip: remove-unnecessary-else, swap-if-else-branches
        with open(htmlFile, "r", encoding="utf-8") as f:
            from_file = await self.find_free_sale(f.read())
        from_html = await self.find_free_sale(html)
        a = []
        b = []
        try:
            for i,j in zip(from_file, from_html):
                if i[1] == "-100%" or j[1] == "-100%":
                    a.append(i)
                    b.append(j)
        except Exception as e:
            self.logger.exception(e)
        a.sort()
        b.sort()
        self.logger.debug(f"SteamLists: {a}, {b}")
        if from_html == from_file or a == b:
            self.logger.debug("Steam File and Html are the same!")
            return True
        else:
            return False

    async def update(self):
        # Check if games from html and saved html are the same, return early.
        # Update if not the same
        html = await self.get_html()
        dupe = await self.dupe_check(html, self.htmlFile)
        if dupe == True:
            return None
        with open(self.htmlFile, "w", encoding="utf-8") as f:
            f.write(html)
            f.close()
        # Get data from html file, and send DM containing free steam games
        sale_data = await self.find_free_sale(html)
        data = await self.get_data() # stored user id's
        embed=discord.Embed(title="Free Steam Game", description="New free Steam Games have been found!", color=0x094d7f)
        # Code below is dupe from the command
        for i in sale_data:
            if i[1] == "-100%":
                name = i[0]
                field_val = i[2]
                embed.add_field(name=name, value=field_val, inline=False)
            else:
                self.logger.debug(i)
                continue
        for id in data["user_id"]:
            user = self.bot.get_user(int(id))
            dm = await user.create_dm()
            if len(embed.fields) != 0:
                await dm.send(embed=embed)
        # timer to fight ratelimits and unnecessary checks in seconds
        # seconds > minutes > hours
        await asyncio.sleep(60*60*6)
        await self.update()

    @app_commands.command(name = "showfreesteam", description= "Get a list of 100% Sale steam games.")
    async def SlashFreeSteam(self, interaction: discord.Interaction):
        html = await self.get_html()
        sale_data = await self.find_free_sale(html)
        embed=discord.Embed(title="Free Steam Game", description="Free Steam Games!", color=0x094d7f)
        # Every 100% Sale game new field
        for i in sale_data:
            if i[1] == "-100%":
                field_val = i[2]
                name = i[0]
                embed.add_field(name=name, value=field_val, inline=False)
        if len(embed.fields) != 0:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No free steam games found.")

    @app_commands.command(name = "remove_free_steam", description = "No longer get notified of free steam games")
    async def slash_RemFreeGames(self, interaction:discord.Interaction):
        data = await self.get_data()
        id_list = data["user_id"]
        if interaction.user.id in id_list:
            id_list.remove(interaction.user.id)
            await interaction.response.send_message("I not notify you of new steam games anymore.", ephemeral=True)
        else:
            await interaction.response.send_message("Not in the list of recipients", ephemeral=True)
        await self.set_data(data)

    @app_commands.command(name = "add_free_steam", description = "Get notified automatically about free steam games")
    async def slash_AddFreeGames(self, interaction:discord.Interaction):
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
