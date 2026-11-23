"""The Profile: a member's own pages, one per feature, across every guild.

A feature adds its page without touching this module. Drop a module into ``web/profile_pages/`` (it is imported
on start-up) and a template under ``templates/profile/``, then register the page there::

    from winter_dragon.web.profile import ProfileContext, profile_page

    @profile_page(slug="fuel", title="Fuel", template="profile/fuel.html")
    def fuel(context: ProfileContext) -> dict[str, object]:
        return {"refuels": list(refuels(context.bind, context.member_id))}

The template extends ``profile/base.html`` and gets the returned dict as its context, plus ``pages`` and ``page``.
The Profile lists the page, serves it at ``/profile/<slug>`` and keeps it to the signed-in member. ``/profile``
reopens the page the member last opened.

A page that has nothing to show until the member uses the feature passes ``used``, a check of whether it has
something for the member. The tab bar puts pages without anything after the others and dims them.
"""

from dataclasses import dataclass, field
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from wd_discord.log import get_logger
lazy from fastapi import HTTPException, Request, status
lazy from sqlalchemy import Engine
lazy from sqlmodel import Session
lazy from starlette.responses import Response
lazy from wd_db.extension.lifecycle import owned_by

from winter_dragon.web.references import References
lazy from winter_dragon.web.accounts import Account, current_account, signed_in, visitor_zone
lazy from winter_dragon.web.responses import database, render_mapping, see_other


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from zoneinfo import ZoneInfo

    from wd_db.extension.lifecycle import LifecycleModel
    from wd_discord.snowflake import Snowflake


logger = get_logger(__name__)
router = APIRouter(prefix="/profile")
LAST_TAB_COOKIE = "profile_tab"
"""Holds the slug of the Profile page the member last opened."""
LAST_TAB_LIFETIME = 60 * 60 * 24 * 365
"""How long, in seconds, the browser keeps :data:`LAST_TAB_COOKIE`: a year."""

type ContextBuilder = Callable[[ProfileContext], Mapping[str, object]]
type UsedCheck = Callable[[Session, ProfileContext], bool]


@dataclass(frozen=True)
class ProfileContext:
    """What a Profile page reads to build itself: the database, the member whose Profile it is, and their time zone."""

    bind: Engine
    member_id: Snowflake
    """The Discord user ID of the signed-in member; a page shows only their records."""
    zone: ZoneInfo
    references: References = field(default_factory=References)
    """Turns a Discord ID into a link to its card; a page puts these in its context and never prints the ID."""


@dataclass(frozen=True)
class ProfilePage:
    """One feature's page in the Profile."""

    slug: str
    """The page's path segment: ``/profile/<slug>``."""
    title: str
    """The page's name in the Profile's list."""
    template: str
    """The Jinja template, extending ``profile/base.html``."""
    context: ContextBuilder
    """Builds the template's context for one member."""
    router: APIRouter | None = None
    """Extra routes of the page, mounted under :attr:`path`."""
    used: UsedCheck | None = None
    """Whether the page has something for a member, given the tab bar's shared session; ``None`` if useful when empty."""

    @property
    def path(self) -> str:
        """The URL the page is served at."""
        return f"{router.prefix}/{self.slug}"


_pages: dict[str, ProfilePage] = {}


def profile_page(
    *,
    slug: str,
    title: str,
    template: str,
    router: APIRouter | None = None,
    used: UsedCheck | None = None,
) -> Callable[[ContextBuilder], ContextBuilder]:
    """Register the decorated function as the context builder of a Profile page; return it unchanged.

    The app mounts ``router``, when given, under the page's path. ``used`` tells the tab bar whether the member
    has anything on the page; without it the page always counts as in use.
    """

    def register(context: ContextBuilder) -> ContextBuilder:
        _pages[slug] = ProfilePage(
            slug=slug,
            title=title,
            template=template,
            context=context,
            router=router,
            used=used,
        )
        return context

    return register


def profile_pages() -> list[ProfilePage]:
    """Return every registered page, by title."""
    load_profile_pages()
    return sorted(_pages.values(), key=lambda page: page.title.casefold())


def has_rows(model: type[LifecycleModel]) -> UsedCheck:
    """Return a ``used`` check that is true when the member owns a row of ``model``."""

    def check(session: Session, context: ProfileContext) -> bool:
        return session.exec(owned_by(model, member=context.member_id).limit(1)).first() is not None

    return check


def tabs(request: Request) -> dict[str, object]:
    """Return the tab bar's context: ``pages`` with the ones in use first, and ``unused``, the slugs of the others.

    Each group stays in title order. Without a signed-in member every page counts as in use.
    """
    pages = profile_pages()
    account = current_account(request)
    if account is None:
        return {"pages": pages, "unused": frozenset[str]()}
    context = ProfileContext(bind=request.app.state.bind, member_id=account.id, zone=visitor_zone(request))
    with Session(context.bind) as session:
        unused = frozenset(page.slug for page in pages if page.used is not None and not _is_used(page, session, context))
    return {"pages": sorted(pages, key=lambda page: page.slug in unused), "unused": unused}


def _is_used(page: ProfilePage, session: Session, context: ProfileContext) -> bool:
    """Run ``page``'s ``used`` check; a check that fails counts as in use, so one broken page leaves the tab bar working."""
    try:
        return page.used is None or page.used(session, context)
    except Exception:
        logger.exception(t"The {page.slug} Profile page's used check failed")
        session.rollback()
        return True


def load_profile_pages() -> None:
    """Import every module in ``web/profile_pages/``, so each registers its page."""
    from importlib import import_module  # noqa: PLC0415
    from pkgutil import iter_modules  # noqa: PLC0415

    from winter_dragon.web import profile_pages as package  # noqa: PLC0415

    for module in iter_modules(package.__path__):
        import_module(f"{package.__name__}.{module.name}")


@router.get("", dependencies=[Depends(signed_in)])
def profile(request: Request) -> Response:
    """Reopen the Profile page the member last opened; without one, show the intro under the tab bar."""
    last = request.cookies.get(LAST_TAB_COOKIE)
    page = next((page for page in profile_pages() if page.slug == last), None)
    if page is not None:
        return see_other(page.path)
    return render_mapping(request, "profile/index.html", {"page": None, **tabs(request)})


@router.get("/{slug}")
def profile_page_view(
    request: Request,
    slug: str,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Show the signed-in member's page ``slug`` of the Profile."""
    page = _page(slug)
    references = References(request.app.state.lookup)
    context = page.context(
        ProfileContext(bind=bind, member_id=account.id, zone=visitor_zone(request), references=references),
    )
    response = render_profile_page(request, slug, context)
    response.set_cookie(
        LAST_TAB_COOKIE,
        page.slug,
        max_age=LAST_TAB_LIFETIME,
        path=router.prefix,
        httponly=True,
        samesite="lax",
    )
    return response


def _page(slug: str) -> ProfilePage:
    """Return the registered page ``slug``; raise a 404 when there is none."""
    page = next((candidate for candidate in profile_pages() if candidate.slug == slug), None)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There's no such Profile page.")
    return page


def render_profile_page(
    request: Request,
    slug: str,
    context: Mapping[str, object],
    *,
    fragment: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Render page ``slug`` with ``context`` plus ``pages`` and ``page`` (whose ``path`` builds its URLs).

    With ``fragment``, a template path, only that part of the page is rendered, as htmx swaps it in.
    """
    page = _page(slug)
    if fragment is not None:
        return render_mapping(request, fragment, {"page": page, **context}, status_code=status_code)
    return render_mapping(
        request,
        page.template,
        {**tabs(request), "page": page, **context},
        status_code=status_code,
    )
