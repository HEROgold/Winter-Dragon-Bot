"""The /fuel command group: log refuels, and graph fuel efficiency over time."""

from __future__ import annotations

from datetime import datetime
lazy import asyncio
lazy from io import BytesIO
lazy from typing import TYPE_CHECKING, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import LifecycleModel, Ownership
from wd_types.clock import utc_now
lazy from matplotlib.dates import DateFormatter, date2num
lazy from matplotlib.figure import Figure
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension.lifecycle import owned_by
lazy from wd_discord.files import File

lazy from winter_dragon.config import CogConfig


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from wd_discord import CommandInteraction


class FuelSettings:
    """Settings for /fuel, in its ``cogs.ini`` section."""

    graph_width_inches = CogConfig(10)
    """The width of the efficiency graph, in inches."""
    graph_height_inches = CogConfig(6)
    """The height of the efficiency graph, in inches."""
    graph_filename = CogConfig("fuel_efficiency.png")
    """The file name the efficiency graph is attached as."""


class CarFuels(LifecycleModel, table=True):
    """One refuel a user logged; ``user_id`` is their Discord user ID, and they own it."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id")

    user_id: int = Field(sa_type=BigInteger, index=True)
    amount: float
    """How much fuel was added."""
    distance: float
    """How far was driven since the previous refuel."""
    price: float
    """The total price paid."""
    timestamp: datetime = Field(default_factory=utc_now, sa_type=AwareDateTime)

    @property
    def efficiency(self) -> float:
        """Distance driven per unit of fuel."""
        return self.distance / self.amount


def render_efficiency_graph(refuels: Sequence[CarFuels]) -> bytes:
    """Return a PNG line graph of the efficiency of ``refuels`` over time, oldest first; refuels without fuel are left out."""
    ordered = sorted((refuel for refuel in refuels if refuel.amount > 0), key=lambda refuel: refuel.timestamp)
    figure = Figure(figsize=(FuelSettings.graph_width_inches, FuelSettings.graph_height_inches))
    axes = figure.subplots()
    axes.plot(
        date2num([refuel.timestamp for refuel in ordered]),
        [refuel.efficiency for refuel in ordered],
        marker="o",
        linestyle="-",
        linewidth=2,
        markersize=6,
    )
    axes.set_xlabel("Date")
    axes.set_ylabel("Efficiency (distance per unit)")
    axes.set_title("Fuel Efficiency Over Time")
    axes.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    axes.tick_params(axis="x", labelrotation=45)
    axes.grid(visible=True, alpha=0.3)
    figure.tight_layout()
    buffer = BytesIO()
    figure.savefig(buffer, format="png")
    return buffer.getvalue()


class Fuel(GroupCog, name="fuel", description="Track your car's refuels and fuel efficiency"):
    """Logs a user's refuels and graphs their fuel efficiency."""

    @override
    async def load(self) -> None:
        """Create the refuel table if missing."""
        self.create_tables(CarFuels)

    @Cog.command(name="add", description="Log a refuel: total price, distance driven since the last one, fuel added")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def add(self, interaction: CommandInteraction, price: float, distance: float, amount: float) -> None:
        """Store a refuel for the invoking user."""
        user = interaction.user
        if user is None:
            return
        if min(price, distance, amount) <= 0:
            await interaction.respond("The price, distance and amount must all be more than 0.", ephemeral=True)
            return
        with Session(self.bind) as session:
            session.add(CarFuels(user_id=int(user.id), amount=amount, distance=distance, price=price))
            session.commit()
        await interaction.respond(
            f"Logged a refuel of {amount:g} for {price:g} after {distance:g}: {distance / amount:.2f} distance per unit.\n"
            f"Use {self.mention(self.efficiency)} to see how that changes over time.",
            ephemeral=True,
        )

    @Cog.command(name="efficiency", description="Show a graph of your distance driven per unit of fuel over time")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def efficiency(self, interaction: CommandInteraction) -> None:
        """Reply with a graph of the invoking user's fuel efficiency."""
        user = interaction.user
        if user is None:
            return
        with Session(self.bind) as session:
            refuels = session.exec(owned_by(CarFuels, member=int(user.id))).all()
        if not refuels:
            await interaction.respond(f"You haven't logged a refuel yet. Use {self.mention(self.add)} first.", ephemeral=True)
            return
        await interaction.defer(ephemeral=True)
        graph = await asyncio.to_thread(render_efficiency_graph, refuels)
        await interaction.respond(
            files=[File(FuelSettings.graph_filename, graph, content_type="image/png", description="Fuel efficiency over time")],
            ephemeral=True,
        )
