
import discord
from discord import app_commands

from bot import WinterDragon
from bot._types.cogs import GroupCog
from database.tables import CarFuel as DbFuel


class Fuel(GroupCog):
    graph = app_commands.Group(name="graph", description="Show a graph containing fuel insights.")

    @app_commands.command(name="add", description="Store some data about tanking fuel")
    async def slash_add(self, interaction: discord.Interaction, fuel: int, distance: int, amount: int) -> None:
        with self.session:
            self.session.add(DbFuel(
                user_id=interaction.user.id,
                amount=amount,
                distance=distance,
                price=fuel,
            ))
            self.session.commit()
        await interaction.response.send_message(f"Stored {fuel=}, {distance=}, {amount=}", ephemeral=True)

    @graph.command(name="efficiency", description="Show a graph showing distance traveled per fuel")
    async def slash_efficiency(self, interaction: discord.Interaction) -> None:
        with self.session:
            fuels = self.session.query(DbFuel).filter(DbFuel.user_id == interaction.user.id).all()
            fuels = sorted(fuels, key=lambda x: x.timestamp)
            fuels = [(x.timestamp, x.distance / x.amount) for x in fuels]
            # TODO: plot a graph
        await interaction.response.send_message(fuels, ephemeral=True)



async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Fuel(bot))
