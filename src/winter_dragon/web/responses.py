"""Rendering the dashboard's templates, as a whole page or as the fragment an htmx request swaps in."""

lazy from pathlib import Path
lazy from typing import TYPE_CHECKING

from fastapi.templating import Jinja2Templates
lazy from fastapi import Request, status
lazy from fastapi.responses import RedirectResponse

lazy from winter_dragon.web.accounts import CSRF_FIELD, csrf_token, current_account
lazy from winter_dragon.web.formatting import shown_value


if TYPE_CHECKING:
    from sqlalchemy import Engine
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
    shared = {"account": current_account(request), "csrf_field": CSRF_FIELD, "csrf_token": csrf_token(request)}
    return templates.TemplateResponse(request, name, shared | context, status_code=status_code)


def see_other(url: str) -> RedirectResponse:
    """Redirect a submitted form to the page ``url``, which the browser then loads with a GET."""
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def database(request: Request) -> Engine:
    """Return the database the app was created on; a FastAPI dependency."""
    return request.app.state.bind
