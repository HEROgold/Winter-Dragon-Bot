"""The Profile: a member's own pages, one per feature, across every guild.

A feature adds its page without touching this module. Drop a module into ``web/profile_pages/`` (it is imported
on start-up) and a template under ``templates/profile/``, then register the page there::

    from winter_dragon.web.profile import ProfileContext, profile_page

    @profile_page(slug="fuel", title="Fuel", template="profile/fuel.html")
    def fuel(context: ProfileContext) -> dict[str, object]:
        return {"refuels": list(refuels(context.bind, context.member_id))}

The template extends ``profile/base.html`` and gets the returned dict as its context, plus ``pages`` and ``page``.
The Profile lists the page, serves it at ``/profile/<slug>`` and keeps it to the signed-in member.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
lazy from fastapi import HTTPException, Request, status
lazy from sqlalchemy import Engine  # noqa: TC002 - FastAPI resolves route annotations at runtime
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime

lazy from winter_dragon.web.accounts import Account, signed_in, visitor_zone
lazy from winter_dragon.web.responses import database, render, render_mapping


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from zoneinfo import ZoneInfo


router = APIRouter(prefix="/profile")

type ContextBuilder = Callable[[ProfileContext], Mapping[str, object]]


@dataclass(frozen=True)
class ProfileContext:
    """What a Profile page reads to build itself: the database, the member whose Profile it is, and their time zone."""

    bind: Engine
    member_id: int
    """The Discord user ID of the signed-in member; a page shows only their records."""
    zone: ZoneInfo


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
) -> Callable[[ContextBuilder], ContextBuilder]:
    """Register the decorated function as the context builder of a Profile page; return it unchanged.

    The app mounts ``router``, when given, under the page's path.
    """

    def register(context: ContextBuilder) -> ContextBuilder:
        _pages[slug] = ProfilePage(slug=slug, title=title, template=template, context=context, router=router)
        return context

    return register


def profile_pages() -> list[ProfilePage]:
    """Return every registered page, by title."""
    load_profile_pages()
    return sorted(_pages.values(), key=lambda page: page.title.casefold())


def load_profile_pages() -> None:
    """Import every module in ``web/profile_pages/``, so each registers its page."""
    from importlib import import_module  # noqa: PLC0415
    from pkgutil import iter_modules  # noqa: PLC0415

    from winter_dragon.web import profile_pages as package  # noqa: PLC0415

    for module in iter_modules(package.__path__):
        import_module(f"{package.__name__}.{module.name}")


@router.get("", dependencies=[Depends(signed_in)])
def profile(request: Request) -> Response:
    """Show the signed-in member's Profile: a link to each feature's page."""
    return render(request, "profile/index.html", pages=profile_pages(), page=None)


@router.get("/{slug}")
def profile_page_view(
    request: Request,
    slug: str,
    account: Annotated[Account, Depends(signed_in)],
    bind: Annotated[Engine, Depends(database)],
) -> Response:
    """Show the signed-in member's page ``slug`` of the Profile."""
    page = _page(slug)
    context = page.context(ProfileContext(bind=bind, member_id=account.id, zone=visitor_zone(request)))
    return render_profile_page(request, slug, context)


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
) -> Response:
    """Render page ``slug`` with ``context`` plus ``pages`` and ``page`` (whose ``path`` builds its URLs).

    With ``fragment``, a template path, only that part of the page is rendered, as htmx swaps it in.
    """
    page = _page(slug)
    if fragment is not None:
        return render_mapping(request, fragment, {"page": page, **context})
    return render_mapping(request, page.template, {"pages": profile_pages(), "page": page, **context})
