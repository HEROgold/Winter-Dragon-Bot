"""The redirect page: opens an app link (``steam://...``) from Discord, which only makes http(s) links clickable."""

lazy from typing import TYPE_CHECKING

from fastapi import APIRouter
lazy from fastapi import Request, status
lazy from starlette.responses import Response  # noqa: TC002 - FastAPI resolves route annotations at runtime

lazy from winter_dragon.redirect_link import REDIRECT_PATH, RedirectLink, UnsafeLinkError
lazy from winter_dragon.web.responses import templates


if TYPE_CHECKING:
    from collections.abc import Mapping


router = APIRouter()

MOBILE_HINT = "Sec-CH-UA-Mobile"
"""The client hint Chromium browsers send: ``?1`` on a phone, ``?0`` elsewhere."""
PHONE_AGENTS = ("Mobi", "Android", "iPhone", "iPad")
"""``User-Agent`` tokens of phones and tablets, for browsers that send no :data:`MOBILE_HINT`."""


def is_phone(headers: Mapping[str, str]) -> bool:
    """Whether the request ``headers`` come from a phone: by its client hint, else by its ``User-Agent``."""
    if (hint := headers.get(MOBILE_HINT)) is not None:
        return hint == "?1"
    agent = headers.get("User-Agent", "")
    return any(token in agent for token in PHONE_AGENTS)


@router.get(REDIRECT_PATH)
def open_link(request: Request, uri: str = "", mobile: str | None = None, fallback: str | None = None) -> Response:
    """Open ``uri``, or ``mobile`` on a phone, with a button in case the browser blocks it and a ``fallback`` page.

    Anyone may follow these links, signed in or not: the bot puts them in DMs.
    """
    try:
        link = RedirectLink(uri, mobile=mobile, fallback=fallback)
    except UnsafeLinkError as refused:
        return _page(request, {"error": str(refused)}, status.HTTP_400_BAD_REQUEST)
    return _page(request, {"target": link.target(phone=is_phone(request.headers)), "fallback": link.fallback})


def _page(request: Request, context: dict[str, object], status_code: int = status.HTTP_200_OK) -> Response:
    """Render the redirect page, without the session the other pages share: it has no forms, and sets no cookie."""
    response = templates.TemplateResponse(request, "redirect.html", context, status_code=status_code)
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
