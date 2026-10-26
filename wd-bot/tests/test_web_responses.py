"""Unit tests: the dashboard's response helpers pick a whole page or an htmx fragment the same way for every route."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Router
from starlette.staticfiles import StaticFiles

from winter_dragon.web.responses import STATIC_DIR, after_post, page_or_fragment


ROUTER = Router(routes=[Mount("/static", StaticFiles(directory=STATIC_DIR), name="static")])
"""Where the templates' ``url_for("static", ...)`` links resolve."""


def _request(*, htmx: bool) -> Request:
    headers = [(b"hx-request", b"true")] if htmx else []
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "session": {}, "query_string": b""}
    return Request(scope | {"router": ROUTER})


def test_a_plain_request_gets_the_whole_page() -> None:
    response = page_or_fragment(_request(htmx=False), "error.html", "data/_record_table.html", message="Oops")

    assert b"Something went wrong" in response.body


def test_an_htmx_request_gets_the_fragment_with_the_status_asked_for() -> None:
    request = _request(htmx=True)

    response = page_or_fragment(request, "data/_record_table.html", "error.html", status_code=422, message="Oops")

    assert response.status_code == 422
    assert b"Something went wrong" in response.body


def test_after_a_plain_post_the_browser_is_sent_back_to_the_page() -> None:
    def fragment() -> Response:
        raise AssertionError

    response = after_post(_request(htmx=False), "/reminders", fragment)

    assert response.status_code == 303
    assert response.headers["location"] == "/reminders"


def test_after_an_htmx_post_the_fragment_is_rendered() -> None:
    swapped = Response("fragment")

    assert after_post(_request(htmx=True), "/reminders", lambda: swapped) is swapped
