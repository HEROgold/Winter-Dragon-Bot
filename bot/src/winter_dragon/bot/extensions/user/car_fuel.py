"""Module for storing and managing fuel data."""
import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.database.tables import CarFuels as DbFuel


class Fuel(GroupCog):
    """Cog for managing fuel data."""

    graph = app_commands.Group(name="graph", description="Show a graph containing fuel insights.")

    @app_commands.command(name="add", description="Store some data about tanking fuel")
    async def slash_add(self, interaction: discord.Interaction, fuel: int, distance: int, amount: int) -> None:
        """Store some data about tanking fuel."""
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
        """Show a graph showing distance traveled per fuel."""
        fuels = self.session.exec(select(DbFuel).where(DbFuel.user_id == interaction.user.id)).all()
        fuels = sorted(fuels, key=lambda x: x.timestamp)
        fuels = [(x.timestamp, x.distance / x.amount) for x in fuels]
        # TODO: plot a graph
        await interaction.response.send_message(fuels, ephemeral=True)



async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Fuel(bot=bot))
