"""The landing page, and the data page: everything the bot stores about the signed-in member, and deleting it."""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Form
lazy from fastapi import HTTPException, Request, status
lazy from sqlmodel import Session
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from wd_bot.application import ApplicationId
lazy from wd_bot.bot import invite_url
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.privacy.domain import RETENTION, DeletionStep, deletion_steps, hide_member_data
lazy from winter_dragon.cogs.reminder.domain import owned_reminders
lazy from winter_dragon.config import Settings
lazy from winter_dragon.web.accounts import SignedIn, checked_csrf, current_account, visitor_zone
lazy from winter_dragon.web.formatting import plural
lazy from winter_dragon.web.records import features, member_records, record_table
lazy from winter_dragon.web.responses import Database, after_post, page_or_fragment, render


if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import Engine
    from wd_discord.snowflake import Snowflake

    from winter_dragon.web.accounts import Account


router = APIRouter()


@dataclass(frozen=True)
class DeletionProgress:
    """How far the member's latest deletion request got: each step done, with when."""

    steps: tuple[tuple[DeletionStep, datetime], ...]

    @property
    def pending(self) -> bool:
        """Whether a request is in progress: their data is hidden, but not purged for good yet."""
        done = {step for step, _ in self.steps}
        return DeletionStep.HIDDEN in done and DeletionStep.PURGED not in done

    @property
    def purge_due(self) -> datetime | None:
        """When the data of a pending request is purged for good; ``None`` without one."""
        requested = next((at for step, at in self.steps if step is DeletionStep.REQUESTED), None)
        return None if requested is None or not self.pending else requested + RETENTION


def _your_data(  # noqa: PLR0913 - the deletion section's state is part of what's rendered
    request: Request,
    account: Account,
    bind: Engine,
    fragment: str,
    *,
    confirming: bool = False,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    """Render the data page: the member's records and where their deletion request stands.

    An htmx request gets only the part of it the template ``fragment`` holds.
    """
    return page_or_fragment(
        request,
        "data/page.html",
        fragment,
        status_code=status_code,
        retention_days=RETENTION.days,
        records=list(member_records(bind, account.id)),
        progress=DeletionProgress(steps=tuple(deletion_steps(bind, account.id))),
        zone=visitor_zone(request),
        confirming=confirming,
        error=error,
    )


@dataclass(frozen=True)
class Signposts:
    """What the landing page's signpost arms say a signed-in member will find down each way."""

    reminders: str
    """How many reminders they have set."""
    records: str
    """How many entries the bot stores about them."""


def signposts(bind: Engine, member_id: Snowflake) -> Signposts:
    """Return what the signpost arms say for the member ``member_id``."""
    with Session(bind) as session:
        reminder_count = sum(1 for _ in owned_reminders(session, member_id))
    entry_count = sum(record.count for record in member_records(bind, member_id))
    return Signposts(reminders=plural(reminder_count, "reminder"), records=plural(entry_count, "entry"))


@router.get("/")
def landing(request: Request, bind: Database) -> Response:
    """Show what the bot does, with the way in: signing in, or adding it to a server.

    A signed-in member's signpost arms say what they'll find: their reminders, and what's stored about them.
    """
    invite = invite_url() if ApplicationId.value is not None else None
    account = current_account(request)
    return render(
        request,
        "index.html",
        features=list(features()),
        invite=invite,
        bot_name=Settings.bot_name,
        signposts=signposts(bind, account.id) if account is not None else None,
    )


@router.get("/me")
def data_page(
    request: Request,
    account: SignedIn,
    bind: Database,
) -> Response:
    """Show everything the bot stores about the signed-in member, and the way to delete it."""
    return _your_data(request, account, bind, "data/page.html")


@router.get("/me/records/{key}")
def record_rows(
    request: Request,
    key: str,
    account: SignedIn,
    bind: Database,
) -> Response:
    """Show the signed-in member's rows of the table ``key``, when its record is opened."""
    table = record_table(bind, account.id, key, visitor_zone(request))
    if table is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There's no such record.")
    return render(request, "data/_record_table.html", table=table)


@router.get("/me/deletion")
def deletion_ask(
    request: Request,
    account: SignedIn,
    bind: Database,
) -> Response:
    """Show the deletion section as it first is: what deleting does, and the button to start."""
    return _your_data(request, account, bind, "data/_deletion.html")


@router.get("/me/deletion/confirm")
def deletion_confirm(
    request: Request,
    account: SignedIn,
    bind: Database,
) -> Response:
    """Ask the member to type their username, to confirm they mean to delete their data."""
    return _your_data(request, account, bind, "data/_deletion.html", confirming=True)


@router.post("/me/deletion", dependencies=[Depends(checked_csrf)])
def request_deletion(
    request: Request,
    account: SignedIn,
    bind: Database,
    confirm_name: Annotated[str, Form()] = "",
) -> Response:
    """Hide all of the member's data for their deletion request, once they typed their username to confirm it."""
    if confirm_name.strip() != account.username:
        error = f"Type {account.username} exactly, to confirm."
        unprocessable = status.HTTP_422_UNPROCESSABLE_CONTENT
        return _your_data(
            request,
            account,
            bind,
            "data/_your_data.html",
            confirming=True,
            error=error,
            status_code=unprocessable,
        )
    hide_member_data(bind, account.id, utc_now())
    return after_post(request, "/me", lambda: _your_data(request, account, bind, "data/_your_data.html"))
