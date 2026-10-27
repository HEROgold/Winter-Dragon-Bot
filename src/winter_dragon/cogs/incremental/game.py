"""The Incremental game's rules, with no Discord in it, so the Discord cog and the dashboard play the same game.

Every function takes a session and a member's Discord user ID. Each one is a whole unit of work and commits.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

lazy from sqlalchemy.exc import IntegrityError
lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive, create_or_restore
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.incremental.catalogue import Catalogue, Currency, Generator, Quantity, catalogue
lazy from winter_dragon.cogs.incremental.models import IncrementalSave, SaveBalance, SaveGenerator


if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class Holding:
    """How much of a currency a save holds right now, and how fast it grows."""

    currency: Currency
    amount: float
    per_second: float


@dataclass(frozen=True)
class Offer:
    """A generator a save can buy: how many it owns, what the next one costs, and whether it can pay."""

    generator: Generator
    owned: int
    price: tuple[Quantity, ...]
    affordable: bool


@dataclass(frozen=True)
class SaveView:
    """A save at one moment: what it holds, and what it can buy."""

    member_id: int
    as_of: datetime
    holdings: tuple[Holding, ...]
    offers: tuple[Offer, ...]


def _balances(session: Session, save_id: int) -> dict[str, SaveBalance]:
    rows = session.exec(alive(SaveBalance).where(SaveBalance.save_id == save_id)).all()
    return {row.currency: row for row in rows}


def _owned(session: Session, save_id: int) -> dict[str, SaveGenerator]:
    rows = session.exec(alive(SaveGenerator).where(SaveGenerator.save_id == save_id)).all()
    return {row.generator: row for row in rows}


def _rates(game: Catalogue, owned: dict[str, SaveGenerator]) -> dict[str, float]:
    """Return the per-second production of each currency for the generators in ``owned``; unknown keys make nothing."""
    rates: dict[str, float] = {}
    for key, row in owned.items():
        if (generator := game.generator(key)) is None:
            continue
        for made in generator.produces:
            rates[made.currency] = rates.get(made.currency, 0.0) + made.amount * row.owned
    return rates


def _amounts(game: Catalogue, balances: dict[str, SaveBalance], rates: dict[str, float], seconds: float) -> dict[str, float]:
    """Return each catalogue currency's stored amount plus ``seconds`` of production.

    A currency never stored (added to the catalogue after the save was made) starts at its starting amount.
    """
    amounts: dict[str, float] = {}
    for currency in game.currencies:
        stored = balances[currency.key].amount if currency.key in balances else currency.starting_amount
        amounts[currency.key] = stored + rates.get(currency.key, 0.0) * seconds
    return amounts


def _view(session: Session, save: IncrementalSave, now: datetime) -> SaveView:
    game = catalogue()
    owned = _owned(session, save.id)
    rates = _rates(game, owned)
    seconds = max(0.0, (now - save.settled_at).total_seconds())
    amounts = _amounts(game, _balances(session, save.id), rates, seconds)
    offers: list[Offer] = []
    for generator in game.generators:
        count = owned[generator.key].owned if generator.key in owned else 0
        price = tuple(generator.price_for(count))
        offers.append(Offer(generator, count, price, all(amounts[cost.currency] >= cost.amount for cost in price)))
    holdings = tuple(Holding(currency, amounts[currency.key], rates.get(currency.key, 0.0)) for currency in game.currencies)
    return SaveView(int(save.id), now, holdings, tuple(offers))


def _store[M: (SaveBalance, SaveGenerator)](session: Session, existing: M | None, row: M) -> None:
    """Write ``row``'s values over the alive ``existing`` row, or create ``row`` (restoring a soft-deleted twin)."""
    if existing is None:
        create_or_restore(session, row)
        return
    for name, value in row.model_dump(exclude={"id", "created_at", "updated_at", "deleted_at"}).items():
        setattr(existing, name, value)
    session.add(existing)


def _find(session: Session, member_id: int, *, lock: bool = False) -> IncrementalSave | None:
    statement = alive(IncrementalSave).where(col(IncrementalSave.id) == member_id)
    return session.exec(statement.with_for_update() if lock else statement).first()


def _ensure_save(session: Session, member_id: int, now: datetime, *, lock: bool = False) -> IncrementalSave:
    """Return the member's save, creating it first when they have none; two creations racing end up with one save."""
    if (save := _find(session, member_id, lock=lock)) is not None:
        return save
    try:
        create_or_restore(session, IncrementalSave(id=member_id, settled_at=now))
        session.commit()
    except IntegrityError:
        session.rollback()
    save = _find(session, member_id, lock=lock)
    if save is None:
        msg = f"Could not create the Incremental save of member {member_id}"
        raise RuntimeError(msg)
    return save


def find_save(session: Session, member_id: int, *, now: datetime | None = None) -> SaveView | None:
    """Return the member's save as of ``now``, or ``None`` when they have none; unlike :func:`open_save` it creates nothing."""
    now = utc_now() if now is None else now
    save = _find(session, member_id)
    return None if save is None else _view(session, save, now)


def open_save(session: Session, member_id: int, *, now: datetime | None = None) -> SaveView:
    """Return the member's save as of ``now`` (default: the current time), creating it on first use.

    Production since the save was last stored is included, however long that was. Reading doesn't change the stored amounts.
    """
    now = utc_now() if now is None else now
    return _view(session, _ensure_save(session, member_id, now), now)


def buy(session: Session, member_id: int, generator_key: str, *, now: datetime | None = None) -> SaveView:
    """Buy one generator for the member and return the save afterwards.

    The save row is locked for the whole transaction, so two buys on one save run one after the other. Each settles
    production, checks the price against what is left, spends and adds.

    Raises:
        Refused: the catalogue has no such generator, or the save can't pay for it.

    """
    now = utc_now() if now is None else now
    game = catalogue()
    generator = game.generator(generator_key)
    if generator is None:
        msg = "That generator doesn't exist."
        raise Refused(msg)
    _ensure_save(session, member_id, now)
    try:
        save = _ensure_save(session, member_id, now, lock=True)
        balances = _balances(session, save.id)
        owned = _owned(session, save.id)
        seconds = max(0.0, (now - save.settled_at).total_seconds())
        amounts = _amounts(game, balances, _rates(game, owned), seconds)
        count = owned[generator.key].owned if generator.key in owned else 0
        for cost in generator.price_for(count):
            if amounts[cost.currency] < cost.amount:
                currency = game.currency(cost.currency)
                name = currency.name if currency is not None else cost.currency
                msg = f"You need {cost.amount:,.1f} {name} for a {generator.name}, but you have {amounts[cost.currency]:,.1f}."
                raise Refused(msg)  # noqa: TRY301 - the rollback below releases the lock
            amounts[cost.currency] -= cost.amount
        for key, amount in amounts.items():
            _store(session, balances.get(key), SaveBalance(save_id=save.id, currency=key, amount=amount))
        _store(session, owned.get(generator.key), SaveGenerator(save_id=save.id, generator=generator.key, owned=count + 1))
        save.settled_at = now
        session.add(save)
        session.commit()
    except BaseException:
        session.rollback()
        raise
    return open_save(session, member_id, now=now)
