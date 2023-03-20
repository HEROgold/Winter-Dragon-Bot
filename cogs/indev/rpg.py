from enum import Enum
import logging
import os
import pickle
import random
from typing import Any, Iterable, List, Optional

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands

import config
import rainbow
from tools import dragon_database


class Item:
    item_name: str
    price: int
    rarity: int
    icon: str
    item_type: str

    def __init__(
            self,
            **kwargs
        ) -> None:
        for key, value in kwargs.items():
            # Use setattr, to allow ANY types like damage, durability etc.
            setattr(self, key, value)

class Fish(Enum):
    COD = Item(
        item_name = "Cod",
        price = 10,
        rarity = 80,
        item_type = "fish",
    )
    SALMON = Item(
        item_name =" Salmon",
        price = 12,
        rarity = 70,
        item_type = "fish",
    )
    PUFFERFISH = Item(
        item_name = "Pufferfish",
        price = 8,
        rarity = 50,
        item_type = "fish",
    )

class Gems(Enum):
    DIAMOND = Item(
        item_name="Diamond",
        price = 125,
        rarity = 20,
        item_type = "gem",
    )

class Stones(Enum):
    STONE = Item(
        item_name = "Stone",
        price = 2,
        rarity = 100,
        item_type = "stone"
    )

class Tools:
    RARITY = 0

class Pickaxes(Tools, Enum):
    STONE_PICKAXE = Item(
        item_name = "Stone Pickaxe",
        price = 120,
        rarity = Tools.RARITY,
        item_type = "pickaxe",
    )        
    IRON_PICKAXE = Item(
        item_name = "Iron Pickaxe",
        price = 640,
        rarity = Tools.RARITY,
        item_type = "pickaxe",
    )

class FishingRods(Tools, Enum):
    WOOD = Item(
        item_name = "Wooden Fishing Rod",
        price = 60,
        rarity = Tools.RARITY,
        item_type = "fishing_rod",
    )
    MYSTERIOUS = Item(
        item_name = "Mysterious Fishing Rod",
        price = 165,
        rarity = Tools.RARITY,
        item_type = "fishing_rod",
    )

class Player:
    player_id: int
    balance: int
    xp: int
    level: int
    xp_multiplier: int | float
    inventory: List[Item]

    def __init__(
            self,
            p_id:int,
            rpg_data:dict=None
        ) -> None:
        if rpg_data is not None:
            for key in rpg_data:
                if key == "inventory":
                    Rpg._inventory_dict_to_obj(self=None, data=rpg_data[key]) # type: ignore
                setattr(self, key, rpg_data[key])
        else:
            self.player_id = p_id
            self.balance = 0
            self.xp = 0
            self.inventory = []
        self._calc_level()

    def _calc_level(self) -> None:
        self.level = self.xp >> 7
        self.xp_multiplier = ((1+(self.level / 100)) if self.level >= 1 else 1)
        logging.getLogger(
            f"{config.Main.BOT_NAME}.{Rpg.__name__}.{self.__class__.__name__}"
        ).debug(
            f"New level of {self.player_id} is {self.level}, with new multiplier {self.xp_multiplier:.2f}"
        )

    def add_xp(self, xp: int) -> None:
        logging.getLogger(
            f"{config.Main.BOT_NAME}.{Rpg.__name__}.{self.__class__.__name__}"
        ).debug(
            f"Adding {xp} XP to {self.xp} with multiplier {self.xp_multiplier:.2f}"
        )
        self.xp += int(xp * self.xp_multiplier)
        self._calc_level()

    def bal_to_coin(self) -> dict[str, int]:
        bronze_coin = str(self.balance)[-2:]
        silver_coin = str(self.balance)[-5:-3]
        gold_coin = str(self.balance)[-8:-6]
        platinum_coin = str(self.balance)[:-8]
        result = {
            "bronze": bronze_coin,
            "silver": silver_coin,
            "gold": gold_coin,
            "platinum": platinum_coin,
        }
        logging.getLogger(
            f"{config.Main.BOT_NAME}.{Rpg.__name__}.{self.__class__.__name__}"
        ).debug(
            f"Converted {self.balance} to {result}"
        )
        return result

class Enemy:
    health: int = 100
    armor: int = 0
    inventory: Optional[List[Item]]

class Rpg(commands.GroupCog, group_name="rpg", group_description="Desc"):
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
            db = dragon_database.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = self.get_data()
        if not self.data:
            self.data = {"players":{}}
        # self.logger.debug(self.data)

    async def cog_unload(self) -> None:
        # self.logger.debug(f"{self.data}")
        self.set_data(self.data)

    def check_item_by_types(self, items:Iterable[Item], *type_to_check:str) -> bool:
        """Check if item type exists in Iterable

        Args:
            items (list[Item]): Iterable of items
            *arg (str): Item types to check

        Returns:
            bool: True, False
        """
        for item_type in type_to_check:
            checked = [item.item_type in item_type for item in items]
            self.logger.debug(f"{checked=}")
            if checked:
                break
        else:
            return True
        return False

    def get_player_obj_data(self, player_id: int) -> Player:
        """Get existing player object, or create new one when it doesn't exist yet."""
        try:
            player = Player(
                p_id = player_id,
                rpg_data=self.data["players"][str(player_id)]
            )
            player.inventory = self._inventory_dict_to_obj(self.data["players"][str(player_id)]["inventory"])
        except KeyError:
            player = Player(
                p_id=player_id
            )
            player.inventory.append(Pickaxes.STONE_PICKAXE.value)
            player.inventory.append(FishingRods.WOOD.value)
        self.logger.debug(f"Returning player data: {player.__dict__}")
        return player

    def _inventory_dict_to_obj(self, data: dict) -> list[Item]:
        return[
            Item(kwargs=item_d)
            for item_d in data
        ]

    async def save_player_obj_data(self, player: Player) -> None:
        """Save player object"""
        try:
            player_data = player.__dict__
            player_data["inventory"] = self._inventory_obj_to_dict(player)
            self.data["players"][str(player.player_id)] = player_data
            self.logger.debug(f"p_data: {player_data}")
            self.set_data(self.data)
        except KeyError as e:
            self.logger.exception(f"No player data to save: {e}")

    def _inventory_obj_to_dict(self, player: Player) -> list[dict[str, Any]]:
        return [
            (item if type(item) == dict else item.__dict__)
            for item in player.inventory
        ]

    def get_random_from_pool(self, pool:list[Item], amount:int=1) -> Item | list[Item]:
        """Get a random item from a pool, including weights.

        Args:
            pool (list[Item]): List of Item from where to fetch
            amount (int, optional): Get X amount of items from given pool. Defaults to 1.

        Returns:
            Item | list[Item]: Returns Item or a list of Item
        """
        self.logger.debug(f"getting items from pool=`{pool}`")
        for item in pool:
            self.logger.debug(f"{item.__dict__}")
        if amount == 1:
            return random.choices(pool, [i.rarity for i in pool], k=amount)[0]
        return random.choices(pool, [i.rarity for i in pool], k=amount)

    jobs = app_commands.Group(name="jobs", description="Get your jobs done.")

    @jobs.command(
        name="fish",
        description="Try to catch some fish"
    )
    # @app_commands.checks.cooldown(2, 300)
    async def jobs_fish(self, interaction:discord.Interaction) -> None:
        player = self.get_player_obj_data(interaction.user.id)
        if not self.check_item_by_types(player.inventory, "fishing_rod", "spear"):
            await interaction.response.send_message("You don't have any fishing tools.", ephemeral=True)
            return
        item = self.get_random_from_pool([fish.value for fish in Fish])
        player.inventory.append(item)
        old = player.xp
        player.add_xp(random.randint(1,4))
        new = player.xp
        xp_gain = new - old
        await self.save_player_obj_data(player)
        await interaction.response.send_message(f"You caught {item.item_name} and gained {xp_gain} XP", ephemeral=True)

    @jobs.command(
        name="mine",
        description="Go to the mine's!"
    )
    # @app_commands.checks.cooldown(2, 300)
    async def jobs_mine(self, interaction:discord.Interaction) -> None:
        player = self.get_player_obj_data(interaction.user.id)
        if not self.check_item_by_types(player.inventory, "pickaxe"):
            await interaction.response.send_message("You don't have a pickaxe.")
            return
        gem = self.get_random_from_pool([gem.value for gem in Gems])
        stone = self.get_random_from_pool([stone.value for stone in Stones])
        item = random.choice([gem, stone])
        player.inventory.append(item)
        old = player.xp
        player.add_xp(random.randint(1,7))
        new = player.xp
        xp_gain = new - old
        await self.save_player_obj_data(player)
        await interaction.response.send_message(f"You mined {item.item_name} and gained {xp_gain} XP")

    inventory = app_commands.Group(name="inventory", description="Manage your inventory.")

    @inventory.command(
        name="show",
        description="Show your inventory"
    )
    async def inventory_show(self, interaction:discord.Interaction, page:int=1) -> None:
        player = self.get_player_obj_data(interaction.user.id)
        await interaction.response.send_message(f"{player.inventory}", ephemeral=True)

    # TODO: rewrite trade system. Allow for lobbies? See TicTacToe.py for lobbies.
    trade = app_commands.Group(name="trade", description="Trade with other players.")

    @trade.command(
            name="start",
            description="Trade"
    )
    async def trade_start(self, interaction:discord.Interaction, player:discord.Member|discord.User) -> None:
        trade_inventory = []
        user = interaction.user
        p1 = self.get_player_obj_data(user.id)
        p2 = self.get_player_obj_data(player.id)
        trade_inventory ^= p1.inventory
        trade_inventory ^= p2.inventory
        self.logger.debug(f"{trade_inventory}")

        embed=discord.Embed(title="Coins", description="description", color=random.choice(rainbow.RAINBOW))
        coins1 = p1.bal_to_coin()
        for k, v in coins1.items():
            embed.add_field(name=k, value=v, inline=True)
        coins2 = p2.bal_to_coin()
        for k, v in coins2.items():
            embed.add_field(name=k, value=v, inline=True)
        await interaction.response.send_message(f"{trade_inventory}", embed=embed)

    shops = app_commands.Group(name="shops", description="For all your buying and selling")

    @shops.command(name="buy", description="Buy stuff")
    async def shops_buy(self, interaction:discord.Interaction, item_name:str, count:int) -> None:
        self.SHOPITEMS = [
                Pickaxes.STONE_PICKAXE.value,
                FishingRods.WOOD.value,
                Gems.DIAMOND.value,
            ]
        for item in self.SHOPITEMS:
            item:Item
            if item.item_name == item_name:
                total_price = item.price * count
                break
        else:
            await interaction.response.send_message(f"{item_name} is not being sold.\nBuyable: {self.SHOPITEMS}", ephemeral=True)
            return
        player = Player(interaction.user.id)
        if total_price > player.balance:
            await interaction.response.send_message(f"Not enough money to buy {count} of {item.item_name}", ephemeral=True)
            return
        for _ in range(count):
            player.inventory.append(item)
            player.balance = player.balance - item.price
        await self.save_player_obj_data(player)
        await interaction.response.send_message(f"Bought {count} of {item.item_name} for {total_price}", ephemeral=True)

    # TODO: Test if this even works
    @shops_buy.autocomplete("item_name")
    async def shops_buy_autocomplete_item_name(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=item.item_name, value=item.item_name)
            for item in self.SHOPITEMS or [Pickaxes.STONE_PICKAXE.value, FishingRods.WOOD.value]
            if current.lower() in item.item_name.lower()
        ]

    @shops.command(name="sell", description="Sell stuff")
    async def shops_sell(self, interaction:discord.Integration, item_name:str, count:int) -> None:
        pass

    # Test if this even works
    @shops_sell.autocomplete("item_name")
    async def shops_sell_autocomplete_item_name(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=iname.item_name, value=iname.item_name)
            for iname in self.get_player_obj_data(interaction.user.id).inventory
            if current.lower() in iname.item_name.lower()
        ]

    @app_commands.command(name="test", description="Test some stuff")
    async def rpg_test(self, interaction: discord.Interaction) -> None: # NOSONAR
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        test_player, tests = await self._run_tests(interaction)
        self.logger.debug(f"tests results: {test_player.__dict__=}")
        emb = discord.Embed(title="Tests")
        for k, v in tests.items():
            emb.add_field(name=k, value=("Succes" if v is True else "Failed"), inline=False)
        await interaction.response.send_message("Test complete", ephemeral=True, embed=emb)

    async def _run_tests(self, interaction: discord.Interaction) -> tuple[Player, dict]:
        tests = {
            "fetch_data": None,
            "bal_change": None,
            "add_xp": None,
            "add_items": None,
            "bal_convertion": None,
            "saving": None
        }
        try:
            test_player = self.get_player_obj_data(interaction.user.id)
            tests["fetch_data"] = True
        except Exception as e:
            self.logger.exception(e)
            try:
                test_player = Player(12345)
            except Exception as e:
                self.logger.exception(e)
            tests["fetch_data"] = False
        try:
            self._test_add_balance(test_player)
            tests["bal_change"] = True
        except Exception as e:
            self.logger.exception(e)
            tests["bal_change"] = False
        try:
            self._test_add_xp(test_player)
            tests["add_xp"] = True
        except Exception as e:
            self.logger.exception(e)
            tests["add_xp"] = False
        try:
            self._test_add_items(test_player)
            tests["add_items"] = True
        except Exception as e:
            self.logger.exception(e)
            tests["add_items"] = False
        try:
            test_player.bal_to_coin()
            tests["bal_convertion"] = True
        except Exception as e:
            self.logger.exception(e)
            tests["bal_convertion"] = False
        try:
            await self.save_player_obj_data(test_player)
            tests["saving"] = True
        except Exception as e:
            self.logger.exception(e)
            tests["saving"] = False
        return test_player, tests

    def _test_add_balance(self, test_player: Player) -> None:
        for _ in range(random.randint(1, 10)):
            test_player.balance += 1234567

    def _test_add_xp(self, test_player: Player) -> None:
        for _ in range(random.randint(1, 10)):
            test_player.add_xp(random.randint(1, 1000))

    def _test_add_items(self, test_player: Player) -> None:
        pool: list[Enum] = []
        pool.extend(Pickaxes)
        pool.extend(FishingRods)
        pool.extend(Fish)
        pool.extend(Gems)
        pool.extend(Stones)
        for item in self.get_random_from_pool(
                [item.value for item in pool], random.randint(2, 10)):
            test_player.inventory.append(item)

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Rpg(bot))
