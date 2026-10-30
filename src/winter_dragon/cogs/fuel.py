"""The /fuel command group: log refuels, and graph fuel efficiency over time."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
lazy import asyncio
lazy from datetime import UTC, date, time
lazy from io import BytesIO
lazy from typing import TYPE_CHECKING, ClassVar, override

from sqlalchemy import BigInteger
from sqlmodel import Field, Session
from wd_bot.commands import Describe, Lookup
from wd_db.extension.columns import AwareDateTime
from wd_db.extension.lifecycle import DiscordKeyedModel, LifecycleModel, Ownership
from wd_types.clock import utc_now
lazy from matplotlib.dates import DateFormatter, date2num
lazy from matplotlib.figure import Figure
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_db.extension.lifecycle import owned_by, upsert
lazy from wd_discord.files import File
lazy from wd_discord.interactions import ApplicationCommandOptionChoice
lazy from wd_errors import Refused

lazy from winter_dragon.config import CogConfig
lazy from winter_dragon.ui import CreatedEmbed


if TYPE_CHECKING:
    lazy from collections.abc import Sequence

    lazy from wd_discord import AutocompleteInteraction, CommandInteraction
    lazy from wd_discord.snowflake import Snowflake


class FuelSettings:
    """Settings for /fuel, in its ``cogs.ini`` section."""

    graph_width_inches = CogConfig(10)
    """The width of the efficiency graph, in inches."""
    graph_height_inches = CogConfig(6)
    """The height of the efficiency graph, in inches."""
    graph_filename = CogConfig("fuel_efficiency.png")
    """The file name the efficiency graph is attached as."""


class FuelUnits(StrEnum):
    """How a member wants fuel efficiency shown; refuels are stored as distance and amount either way."""

    KM_PER_L = "km/L"
    L_PER_100_KM = "L/100km"

    def convert(self, km_per_l: float) -> float:
        """Return ``km_per_l`` in these units; a value of 0 or less has no L/100km, so it gives 0."""
        if self is FuelUnits.L_PER_100_KM:
            return 100 / km_per_l if km_per_l > 0 else 0.0
        return km_per_l


class FuelPreferences(DiscordKeyedModel, table=True):
    """A member's fuel settings; ``id`` is their Discord user ID, and they own it."""

    ownership: ClassVar[Ownership] = Ownership(member="id")

    units: FuelUnits = FuelUnits.KM_PER_L
    """The units fuel efficiency is shown in."""


def member_units(session: Session, user_id: Snowflake) -> FuelUnits:
    """Return the units ``user_id`` picked, or km/L when they never did."""
    preferences = session.get(FuelPreferences, int(user_id))
    return FuelUnits.KM_PER_L if preferences is None or preferences.deleted_at is not None else preferences.units


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
    """When the entry was made."""
    refueled_at: datetime | None = Field(default=None, sa_type=AwareDateTime)
    """The day the member refueled; empty on refuels logged before it existed, which fall back to ``timestamp``."""

    @property
    def refuel_date(self) -> datetime:
        """When the refuel happened: ``refueled_at``, or the entry time when that is empty."""
        return self.timestamp if self.refueled_at is None else self.refueled_at

    @property
    def efficiency(self) -> float:
        """Distance driven per unit of fuel (km/L)."""
        return self.distance / self.amount

    def efficiency_in(self, units: FuelUnits) -> float:
        """Return the efficiency of this refuel in ``units``."""
        return units.convert(self.efficiency)


def parse_refuel_date(value: str) -> datetime | None:
    """Return midnight UTC of the ``YYYY-MM-DD`` day in ``value``, or ``None`` when it isn't one."""
    try:
        day = date.fromisoformat(value.strip())
    except ValueError:
        return None
    return datetime.combine(day, time(), tzinfo=UTC)


def graphable(refuels: Sequence[CarFuels], units: FuelUnits = FuelUnits.KM_PER_L) -> list[tuple[datetime, float]]:
    """Return the ``(date, efficiency in units)`` of each of ``refuels`` that added fuel, oldest first."""
    ordered = sorted((refuel for refuel in refuels if refuel.amount > 0), key=lambda refuel: refuel.refuel_date)
    return [(refuel.refuel_date, refuel.efficiency_in(units)) for refuel in ordered]


def render_efficiency_graph(refuels: Sequence[CarFuels], units: FuelUnits = FuelUnits.KM_PER_L) -> bytes:
    """Return a PNG line graph of the efficiency of ``refuels`` over time, oldest first; refuels without fuel are left out."""
    points = graphable(refuels, units)
    figure = Figure(figsize=(FuelSettings.graph_width_inches, FuelSettings.graph_height_inches))
    axes = figure.subplots()
    axes.plot(
        date2num([day for day, _ in points]),
        [value for _, value in points],
        marker="o",
        linestyle="-",
        linewidth=2,
        markersize=6,
    )
    axes.set_xlabel("Date")
    axes.set_ylabel(f"Efficiency ({units})")
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
        self.create_tables(CarFuels, FuelPreferences)

    @Cog.command(
        name="add",
        description="Log a refuel: total price, distance driven since the last one, fuel added, optional YYYY-MM-DD date",
    )
    async def add(
        self,
        interaction: CommandInteraction,
        price: Annotated[float, Describe("The total price of the refuel")],
        distance: Annotated[float, Describe("The distance driven since the last refuel")],
        amount: Annotated[float, Describe("The amount of fuel added")],
        date: Annotated[str | None, Describe("The day of the refuel as YYYY-MM-DD, now when left out")] = None,
    ) -> None:
        """Store a refuel for the invoking user, dated ``date`` (``YYYY-MM-DD``, UTC) or now.

        Raises:
            Refused: When ``date`` isn't a ``YYYY-MM-DD`` day, or is in the future.

        """
        user = interaction.user
        if user is None:
            return
        if min(price, distance, amount) <= 0:
            msg = "The price, distance and amount must all be more than 0."
            raise Refused(msg)
        now = utc_now()
        refueled_at = now if date is None else parse_refuel_date(date)
        if refueled_at is None:
            msg = "The date must be written as YYYY-MM-DD."
            raise Refused(msg)
        if refueled_at > now:
            msg = "The date can't be in the future."
            raise Refused(msg)
        with Session(self.bind) as session:
            session.add(
                CarFuels(
                    user_id=int(user.id),
                    amount=amount,
                    distance=distance,
                    price=price,
                    timestamp=now,
                    refueled_at=refueled_at,
                ),
            )
            session.commit()
            units = member_units(session, user.id)
        logged = (
            f"Logged a refuel of {amount:g} for {price:g} after {distance:g}: {units.convert(distance / amount):.2f} {units}.\n"
            f"Use {self.mention(self.efficiency)} to see how that changes over time."
        )
        await interaction.respond(embeds=[CreatedEmbed(description=logged)], ephemeral=True)

    @Cog.command(name="efficiency", description="Show a graph of your fuel efficiency over time, in your units")
    async def efficiency(self, interaction: CommandInteraction) -> None:
        """Reply with a graph of the invoking user's fuel efficiency."""
        user = interaction.user
        if user is None:
            return
        with Session(self.bind) as session:
            refuels = session.exec(owned_by(CarFuels, member=user.id)).all()
            units = member_units(session, user.id)
        if not refuels:
            msg = f"You haven't logged a refuel yet. Use {self.mention(self.add)} first."
            raise Refused(msg)
        await interaction.defer(ephemeral=True)
        graph = await asyncio.to_thread(render_efficiency_graph, refuels, units)
        await interaction.respond(
            files=[File(FuelSettings.graph_filename, graph, content_type="image/png", description="Fuel efficiency over time")],
            ephemeral=True,
        )

    async def units_choices(self, interaction: AutocompleteInteraction, current: str) -> list[ApplicationCommandOptionChoice]:  # noqa: ARG002 - fixed list
        """Suggest the units that contain what was typed."""
        return [
            ApplicationCommandOptionChoice(name=unit.value, value=unit.value)
            for unit in FuelUnits
            if current.lower() in unit.value.lower()
        ]

    @Cog.command(name="units", description="Pick how your fuel efficiency is shown: km/L or L/100km")
    async def units(
        self,
        interaction: CommandInteraction,
        units: Annotated[str, Lookup(units_choices), Describe("km/L or L/100km")],
    ) -> None:
        """Store the invoking user's fuel efficiency units."""
        user = interaction.user
        if user is None:
            return
        try:
            chosen = FuelUnits(units.strip())
        except ValueError:
            options = " or ".join(unit.value for unit in FuelUnits)
            await interaction.respond(f"Pick {options}.", ephemeral=True)
            return
        with Session(self.bind) as session:
            upsert(session, FuelPreferences(id=int(user.id), units=chosen))
            session.commit()
        await interaction.respond(f"Your fuel efficiency is now shown in {chosen}.", ephemeral=True)
