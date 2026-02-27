"""Module for storing and managing fuel data."""

import discord
import matplotlib.dates as mdates
from discord import app_commands
from matplotlib import pyplot as plt
from sqlmodel import select
from winter_dragon.database.tables import CarFuels as DbFuel

from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.core.paths import IMG_DIR


class Fuel(GroupCog, auto_load=True):
    """Cog for managing fuel data."""

    graph = app_commands.Group(name="graph", description="Show a graph containing fuel insights.")

    @app_commands.command(name="add", description="Store some data about tanking fuel")
    @app_commands.describe(
        price="The total price paid for the fuel.",
        distance="The distance traveled since the last refuel.",
        amount="The amount of fuel added.",
    )
    async def slash_add(self, interaction: discord.Interaction, price: float, distance: float, amount: float) -> None:
        """Store some data about tanking fuel."""
        self.session.add(
            DbFuel(
                user_id=interaction.user.id,
                amount=amount,
                distance=distance,
                price=price,
            ),
        )
        self.session.commit()
        await interaction.response.send_message(f"Stored {price=}, {distance=}, {amount=}", ephemeral=True)

    @graph.command(name="efficiency", description="Show a graph showing distance traveled per fuel")
    async def slash_efficiency(self, interaction: discord.Interaction) -> None:
        """Show a graph showing distance traveled per fuel."""
        await interaction.response.defer(thinking=True, ephemeral=True)

        fuels = self.session.exec(select(DbFuel).where(DbFuel.user_id == interaction.user.id)).all()

        if not fuels:
            await interaction.followup.send("No fuel data found. Add some data first using `/add`.", ephemeral=True)
            return

        fuels = sorted(fuels, key=lambda x: x.timestamp)
        timestamps = [x.timestamp for x in fuels]
        efficiencies = [x.distance / x.amount for x in fuels]

        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, efficiencies, marker="o", linestyle="-", linewidth=2, markersize=6)
        plt.xlabel("Date")
        plt.ylabel("Efficiency (distance per unit)")
        plt.title("Fuel Efficiency Over Time")
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid(visible=True, alpha=0.3)

        # Save the plot
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        efficiency_file = IMG_DIR / f"fuel_efficiency_{interaction.user.id}.png"
        plt.savefig(efficiency_file)
        plt.clf()
        plt.close()

        # Send the graph as a file attachment
        try:
            file = discord.File(efficiency_file)
            await interaction.followup.send(file=file, ephemeral=True)
        except Exception:
            self.logger.exception("Error when creating fuel efficiency graph.")
            await interaction.followup.send("Could not create the efficiency graph.", ephemeral=True)
        finally:
            # Clean up the temporary file
            if efficiency_file.exists():
                efficiency_file.unlink()
