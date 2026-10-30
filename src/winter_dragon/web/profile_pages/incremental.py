"""The Profile's Incremental game page: the member's save live in the browser, and buying generators.

The server sends a :class:`Snapshot` (amounts, rates and the time it was taken). The browser ticks the amounts and
countdowns forward from it, and the page asks for a new snapshot every :data:`RESYNC_SECONDS`, so drift never builds
up. Buying goes through :func:`winter_dragon.cogs.incremental.game.buy`, the same function the Discord buttons call.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
lazy from fastapi import Request
lazy from sqlalchemy import Engine  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from sqlmodel import Session
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from wd_errors import Refused

lazy from winter_dragon.cogs.incremental import game
lazy from winter_dragon.cogs.incremental.view import format_amount, format_quantities
lazy from winter_dragon.web.accounts import Account, checked_csrf, signed_in
lazy from winter_dragon.web.profile import ProfileContext, profile_page, render_profile_page
lazy from winter_dragon.web.responses import database, is_htmx


if TYPE_CHECKING:
    lazy from datetime import datetime

    lazy from wd_discord.snowflake import Snowflake


TEMPLATE = "profile/incremental.html"
FRAGMENT = "profile/_incremental_game.html"
RESYNC_SECONDS = 30
"""How often the page asks the server for a new snapshot."""

router = APIRouter()


@dataclass(frozen=True)
class HoldingSnapshot:
    """One currency in a snapshot."""

    key: str
    label: str
    amount: float
    per_second: float

    @property
    def amount_text(self) -> str:
        """The amount as the page first shows it."""
        return format_amount(self.amount)

    @property
    def rate_text(self) -> str:
        """The production per second as the page shows it."""
        return format_amount(self.per_second)


@dataclass(frozen=True)
class OfferSnapshot:
    """One generator in a snapshot: what the member owns, what the next one costs, and how long until they can pay."""

    key: str
    name: str
    description: str
    owned: int
    price_text: str
    produces_text: str
    affordable: bool
    seconds_until_affordable: float | None
    """``0`` when affordable, ``None`` when the save produces nothing of a currency it lacks."""


@dataclass(frozen=True)
class Snapshot:
    """A save at ``taken_at``; the browser ticks it forward from here."""

    taken_at: datetime
    holdings: tuple[HoldingSnapshot, ...]
    offers: tuple[OfferSnapshot, ...]


def seconds_until_affordable(offer: game.Offer, per_second: dict[str, float], amounts: dict[str, float]) -> float | None:
    """Return how many seconds until the save can pay ``offer``'s price at the current rates, or ``None`` if never."""
    wait = 0.0
    for cost in offer.price:
        missing = cost.amount - amounts[cost.currency]
        if missing <= 0:
            continue
        rate = per_second[cost.currency]
        if rate <= 0:
            return None
        wait = max(wait, missing / rate)
    return wait


def snapshot_of(view: game.SaveView) -> Snapshot:
    """Turn the shared game module's ``view`` into what the page shows and ticks."""
    amounts: dict[str, float] = {holding.currency.key: holding.amount for holding in view.holdings}
    rates: dict[str, float] = {holding.currency.key: holding.per_second for holding in view.holdings}
    return Snapshot(
        taken_at=view.as_of,
        holdings=tuple(HoldingSnapshot(h.currency.key, h.currency.label, h.amount, h.per_second) for h in view.holdings),
        offers=tuple(
            OfferSnapshot(
                key=offer.generator.key,
                name=offer.generator.name,
                description=offer.generator.description,
                owned=offer.owned,
                price_text=format_quantities(offer.price),
                produces_text=format_quantities(offer.generator.produces),
                affordable=offer.affordable,
                seconds_until_affordable=0.0 if offer.affordable else seconds_until_affordable(offer, rates, amounts),
            )
            for offer in view.offers
        ),
    )


def snapshot(bind: Engine, member_id: Snowflake, *, now: datetime | None = None) -> Snapshot | None:
    """Return the member's save as of ``now``, or ``None`` when they haven't started one; this never creates a save."""
    with Session(bind) as session:
        view = game.find_save(session, member_id, now=now)
    return None if view is None else snapshot_of(view)


@profile_page(slug="incremental", title="Incremental", template=TEMPLATE, router=router)
def incremental(context: ProfileContext) -> dict[str, object]:
    """Return the page's context: the member's snapshot, or ``None`` to show how to start a save."""
    return {"snapshot": snapshot(context.bind, context.member_id), "message": None, "resync_seconds": RESYNC_SECONDS}


def _respond(request: Request, account: Account, bind: Engine, *, message: str | None, refused: bool = False) -> Response:
    """Render the game for the signed-in member: the fragment for htmx, the whole page otherwise."""
    context: dict[str, object] = {
        "snapshot": snapshot(bind, account.id),
        "message": message,
        "refused": refused,
        "resync_seconds": RESYNC_SECONDS,
    }
    return render_profile_page(request, "incremental", context, fragment=FRAGMENT if is_htmx(request) else None)


@router.get("/snapshot")
def resync(
    request: Request,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Return the game fragment with a fresh snapshot, which htmx swaps in to re-sync the page."""
    return _respond(request, account, bind, message=None)


@router.post("/start", dependencies=[Depends(checked_csrf)])
def start(
    request: Request,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Create the member's save, as their first ``/incremental`` in Discord does."""
    with Session(bind) as session:
        game.open_save(session, account.id)
    return _respond(request, account, bind, message="Your save is ready.")


@router.post("/buy/{generator}", dependencies=[Depends(checked_csrf)])
def buy(
    request: Request,
    generator: str,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Buy one ``generator`` for the member; a refusal is shown on the page instead of failing the request."""
    try:
        with Session(bind) as session:
            game.buy(session, account.id, generator)
    except Refused as refused:
        return _respond(request, account, bind, message=refused.message, refused=True)
    return _respond(request, account, bind, message="Bought one.")
