from datetime import UTC, datetime, timedelta

import discord
from core.bot import WinterDragon
from core.cogs import GroupCog

from database.tables.incremental import (
    Player as IncrementalPlayer,
)
from database.tables.incremental import (
    UserGenerator,
    UserMoney,
)
from database.tables.incremental.rates import GeneratorRates


type Player = discord.User | discord.Member
# TODO @HEROgold: Use a better type for resources.
# 0
type IncrementalRecources = dict[str, int]

class Incremental(GroupCog):
    def init_player(self, user: Player) -> None:
        # Init player data in database.
        with self.session as session:
            if (
                _ := session.query(IncrementalPlayer)
                .where(IncrementalPlayer.id == user.id)
                .first()
            ):
                return
            session.add(IncrementalPlayer(user_id=user.id))
            session.add(UserMoney(user_id=user.id))
            session.add(UserGenerator(user_id=user.id, generator_id=1))
            session.commit()

    def get_generators(self, user: Player) -> list[UserGenerator]:
        with self.session as session:
            return session.query(UserGenerator).where(UserGenerator.user_id == user.id).all()

    def get_time_difference(self, user: Player) -> timedelta:
        with self.session as session:
            player = session.query(IncrementalPlayer).where(IncrementalPlayer.id == user.id).first()
            if player is None:
                return timedelta(seconds=0)
            current = datetime.now(UTC)
            res = player.last_collection - current
            self.update_collection_time(player, current)
            session.commit()
            return res

    def update_collection_time(self, player: IncrementalPlayer, time_stamp: datetime) -> None:
        player.last_collection = time_stamp

    def get_resources(self, player: Player) -> IncrementalRecources:
        with self.session as session:
            balance = session.query(UserMoney).where(UserMoney.user_id == player.id).first()
            return {"Balance": balance.value}

    def add_resources(self, player: Player) -> None:
        """Add resources to player's inventory based on time difference."""
        time = self.get_time_difference(player)
        generators = self.get_generators(player)
        with self.session as session:
            balance = session.query(UserMoney).where(UserMoney.user_id == player.id).first()
            if not balance:
                return
            for generator in generators:
                rate = session.query(GeneratorRates).where(GeneratorRates.generator_id == generator.generator_id).first()
                amount = int(rate.per_second * time.total_seconds())
                balance.value += amount
            session.commit()
        # TODO @HEROgold: return a embed containing the resources collected.
        # 000

    def generate_embed(self, player: Player, resources: IncrementalRecources) -> discord.Embed:
        with self.session as session:
            balance = session.query(UserMoney).where(UserMoney.user_id == player.id).first()
            embed = discord.Embed(title="Resources Collected", color=discord.Color.green())
            for k, v in resources.items():
                embed.add_field(name=k, value=v, inline=False)
            embed.set_footer(text=f"Total Balance: {balance.value}")
            return embed

    async def slash_collect(self, interaction: discord.Interaction) -> None:
        # Collect resources
        # Get player's generators, calculate resources, and add them to player's inventory.
        player = interaction.user
        self.init_player(player)

        old = self.get_resources(player)
        self.add_resources(player)
        new = self.get_resources(player)
        difference = {k: new[k] - old[k] for k in old}

        self.generate_embed(player, difference)
        await interaction.response.send_message(
            "Resources collected!",
            ephemeral=True,
            embed=self.generate_embed(player, difference),
        )


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Incremental(bot))
