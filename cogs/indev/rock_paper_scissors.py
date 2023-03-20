import logging
import os
import pickle

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands
from discord.ui import Button

import config
from tools import dragon_database_Mongo


class RPSView(discord.ui.View):
    """View created for rock paper scissors. Contains 3 buttons."""
    # TODO: add callbacks
    rock: Button(label="Rock", style=discord.ButtonStyle.blurple)
    paper: Button(label="Paper", style=discord.ButtonStyle.blurple)
    scissor: Button(label="Scissors", style=discord.ButtonStyle.blurple)

    def __init__(self) -> None:
        super().__init__()
        self.add_item(self.rock)
        self.add_item(self.paper)
        self.add_item(self.scissor)


class RockPaperScissors(commands.GroupCog):
    CHOICES = ["rock", "paper", "scissor"]

    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database_Mongo.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database_Mongo.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        self.data = self.get_data()

    async def cog_unload(self) -> None:
        self.set_data(self.data)

    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="new",
        description="Start a rock paper, scissors game, which player can join"
    )
    async def slash_rock_paper_scissors(self, interaction:discord.Interaction, choice:str, oponent:discord.Member=None) -> None:
        if choice not in self.CHOICES:
            await interaction.response.send_message(f"Thats not a valid choice, must be one of {self.CHOICES}", ephemeral=True)
        if oponent:
            e_dm = oponent.dm_channel or await oponent.create_dm()
            await e_dm.send(f"{interaction.user.mention} dueled you in Rock, Paper, Scissors, what's your choice?", view=RPSView())
            await interaction.response.send_message("Duel send", ephemeral=True, delete_after=5)
            return
        await interaction.response.send_message(f"{interaction.user.mention} started Rock, Paper, Scissors, what's your choice?", view=RPSView())
        # self.set_data(self.data)

    @slash_rock_paper_scissors.autocomplete("choice")
    async def rock_paper_scissors_autocoplete_choice(self, interaction:discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.CHOICES
            if current.lower() in i.lower()
        ]


async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(RockPaperScissors(bot)) # type: ignore
