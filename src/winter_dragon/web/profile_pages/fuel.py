"""The Profile's fuel page: an efficiency graph over time and a table of the member's refuels, newest first."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlmodel import Session
lazy from wd_db.extension.lifecycle import owned_by

lazy from winter_dragon.cogs.fuel import CarFuels
lazy from winter_dragon.web.profile import ProfileContext, profile_page


if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime


GRAPH_WIDTH = 600
GRAPH_HEIGHT = 240
GRAPH_PADDING = 36


@dataclass(frozen=True)
class GraphPoint:
    """One refuel on the graph, in SVG coordinates."""

    x: float
    y: float
    label: str
    """What the point's tooltip says."""


@dataclass(frozen=True)
class EfficiencyGraph:
    """The efficiency of a member's refuels over time, ready to draw as an SVG line."""

    points: tuple[GraphPoint, ...]
    lowest: float
    highest: float
    first_day: datetime
    last_day: datetime

    @property
    def line(self) -> str:
        """The ``points`` attribute of the SVG polyline."""
        return " ".join(f"{point.x:.1f},{point.y:.1f}" for point in self.points)


def efficiency_graph(refuels: Sequence[CarFuels]) -> EfficiencyGraph | None:
    """Return the graph of ``refuels``, or ``None`` when none of them added fuel."""
    ordered = sorted((refuel for refuel in refuels if refuel.amount > 0), key=lambda refuel: refuel.refuel_date)
    if not ordered:
        return None
    values = [refuel.efficiency for refuel in ordered]
    lowest, highest = min(values), max(values)
    start, end = ordered[0].refuel_date, ordered[-1].refuel_date
    span_x = GRAPH_WIDTH - 2 * GRAPH_PADDING
    span_y = GRAPH_HEIGHT - 2 * GRAPH_PADDING
    duration = (end - start).total_seconds()
    spread = highest - lowest
    points = tuple(
        GraphPoint(
            x=GRAPH_PADDING + (span_x * (refuel.refuel_date - start).total_seconds() / duration if duration else span_x / 2),
            y=GRAPH_PADDING + (span_y * (1 - (value - lowest) / spread) if spread else span_y / 2),
            label=f"{refuel.refuel_date:%Y-%m-%d}: {value:.2f}",
        )
        for refuel, value in zip(ordered, values, strict=True)
    )
    return EfficiencyGraph(points=points, lowest=lowest, highest=highest, first_day=start, last_day=end)


@profile_page(slug="fuel", title="Fuel", template="profile/fuel.html")
def fuel(context: ProfileContext) -> dict[str, object]:
    """Return the fuel page's context: the member's refuels, newest first, and their efficiency graph."""
    with Session(context.bind) as session:
        refuels = sorted(
            session.exec(owned_by(CarFuels, member=context.member_id)), key=lambda refuel: refuel.refuel_date, reverse=True
        )
    return {
        "refuels": [(refuel, refuel.refuel_date.astimezone(context.zone)) for refuel in refuels],
        "graph": efficiency_graph(refuels),
        "width": GRAPH_WIDTH,
        "height": GRAPH_HEIGHT,
        "padding": GRAPH_PADDING,
    }
