"""Rendering the dashboard's templates, as a whole page or as the fragment an htmx request swaps in."""

lazy from pathlib import Path
lazy from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from fastapi.templating import Jinja2Templates
lazy from fastapi import Request, status
lazy from fastapi.responses import RedirectResponse
lazy from sqlalchemy import Engine

lazy from winter_dragon.web.accounts import CSRF_FIELD, csrf_token, current_account
lazy from winter_dragon.web.formatting import shown_value


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from starlette.responses import Response


TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["shown"] = shown_value  # pyrefly: ignore[unsupported-operation] - typed from the built-in filters only


def is_htmx(request: Request) -> bool:
    """Whether ``request`` came from htmx, which swaps in a fragment instead of loading a page."""
    return request.headers.get("HX-Request") == "true"


def render(request: Request, name: str, *, status_code: int = status.HTTP_200_OK, **context: object) -> Response:
    """Render the template ``name`` with ``context``, plus the signed-in account and the CSRF token every form carries."""
    return render_mapping(request, name, context, status_code=status_code)


def render_mapping(
    request: Request,
    name: str,
    context: Mapping[str, object],
    *,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Like :func:`render`, for a ``context`` built elsewhere, whose keys can't be passed as keyword arguments."""
    shared = {"account": current_account(request), "csrf_field": CSRF_FIELD, "csrf_token": csrf_token(request)}
    return templates.TemplateResponse(request, name, shared | dict(context), status_code=status_code)


def page_or_fragment(
    request: Request,
    page: str,
    fragment: str,
    *,
    status_code: int = status.HTTP_200_OK,
    **context: object,
) -> Response:
    """Render the whole template ``page``, or only the template ``fragment`` when htmx asked, to swap it in."""
    return render(request, fragment if is_htmx(request) else page, status_code=status_code, **context)


def after_post(request: Request, url: str, fragment: Callable[[], Response]) -> Response:
    """Answer a form that went through: send a plain browser back to the page ``url``, or render htmx its ``fragment``."""
    return fragment() if is_htmx(request) else see_other(url)


def see_other(url: str) -> RedirectResponse:
    """Redirect a submitted form to the page ``url``, which the browser then loads with a GET."""
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def database(request: Request) -> Engine:
    """Return the database the app was created on; a FastAPI dependency."""
    return request.app.state.bind


Database = Annotated[Engine, Depends(database)]
"""The database the app was created on, as a route parameter's annotation."""
