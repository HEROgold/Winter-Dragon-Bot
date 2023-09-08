import datetime
import logging
import math
from typing import List

import discord
from discord import app_commands
from discord.components import SelectOption
from discord.ext import commands
from discord.ui import View, Select

from tools.config_reader import config
from tools.database_tables import Session, engine
from tools.database_tables import IncrementalGen as DbGen
from tools.database_tables import Incremental as DbIncremental
from enums.incremental import Generators


def update_balance(incremental: DbIncremental) -> None:
    """Updates the balance of a incremental, based on time past since last increment, and gain rate

    Args:
        incremental (DbIncremental): Db object holding incremental data
    """
    difference = incremental.last_update - datetime.datetime.now()
    seconds = math.floor(difference.total_seconds())

    total_gain_rate = sum(gen.generating for gen in incremental.generators)
    incremental.balance = incremental.balance + total_gain_rate * seconds
    incremental.last_update = datetime.datetime.now()


class ShopItems(Select):
    def __init__(
        self,
        *,
        custom_id: str = "shop",
        placeholder: str | None = None,
        min_values: int = 1,
        max_values: int = 1,
        options: List[SelectOption] = None,
        disabled: bool = False,
        row: int | None = None
    ) -> None:
        placeholder = "Choose generator to buy"

        options = [
            discord.SelectOption(label=i.name, description=f"Tier {i.value}")
            for i in Generators
        ]

        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
            row=row
        )


    async def callback(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            incr = DbIncremental.fetch_user(interaction.user.id)
            selector = self.values[0]
            gen = Generators[selector]

            if self.is_payable(gen, incr):
                incr.balance = incr.balance - gen.value << 2

            session.add(DbGen(
                user_id = interaction.user.id,
                incremental_id = incr.id,
                generator_id = gen.value,
                name = gen.name,
                price = gen.value << 2,
                generating = gen.generation_rate
            ))
            session.commit()
        await interaction.response.send_message(f"Successfully bought {self.values[0]} for {Generators[self.values[0]].value}", ephemeral=True)


    def is_payable(self, generator: Generators, incremental: DbIncremental) -> bool:
        return incremental.balance >= generator.value << 2



class Shop(View):
    timeout = 180

    def __init__(self) -> None:
        super().__init__(timeout=180)

        self.add_item(ShopItems())


class Incremental(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @app_commands.command(name="shop", description="Show the shopping menu")
    async def fetch_account(self, interaction: discord.Interaction) -> None:
        """Send a message, containing the shop view"""
        await interaction.response.send_message(view=Shop(), delete_after=Shop.timeout)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Incremental(bot))
