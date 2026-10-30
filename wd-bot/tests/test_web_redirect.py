"""Unit tests: the dashboard's /redirect page and the links the bot builds to it (no network)."""

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from winter_dragon.cogs import import_cogs
from winter_dragon.redirect_link import REDIRECT_PATH, RedirectLink, UnsafeLinkError
from winter_dragon.web.app import create_app


if TYPE_CHECKING:
    from sqlalchemy import Engine


STEAM = "steam://openurl/https://store.steampowered.com/app/730/"
STORE = "https://store.steampowered.com/app/730/"
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"


@pytest.fixture
def client(engine: Engine) -> TestClient:
    """Return a browser on the dashboard, not signed in."""
    import_cogs()
    SQLModel.metadata.create_all(engine)
    return TestClient(create_app(bind=engine, session_secret="test-secret"))


def _redirect(client: TestClient, user_agent: str = DESKTOP_UA, **query: str) -> tuple[int, str]:
    response = client.get(REDIRECT_PATH, params=query, headers={"User-Agent": user_agent})
    return response.status_code, response.text


# --- Checking links ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "uri",
    [STEAM, "steam://store/730", "steam://install/730", "spotify:track:4uLU6hMCjMI75M1A2tKUQC", "https://example.com/"],
)
def test_any_scheme_but_the_blocked_ones_is_accepted(uri: str) -> None:
    assert RedirectLink(uri).uri == uri


@pytest.mark.parametrize(
    "uri",
    [
        "http://store.steampowered.com/app/730/",
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "blob:https://example.com/1",
        "ftp://example.com/",
        "ws://example.com/",
        "telnet://example.com",
        "ms-msdt:/id PCWDiagnostic",
        "search-ms:query=x",
        "view-source:https://example.com/",
    ],
)
def test_blocked_schemes_are_refused(uri: str) -> None:
    with pytest.raises(UnsafeLinkError):
        RedirectLink(uri)


@pytest.mark.parametrize(
    "uri",
    [
        "",
        " ",
        "store.steampowered.com/app/730/",
        "/relative/path",
        "//evil.example/",
        " javascript:alert(1)",
        "\tjavascript:alert(1)",
        "java\nscript:alert(1)",
        "javascript%3Aalert(1)",
        "%6Aavascript:alert(1)",
        "steam://store/730 ",
        "1steam://store/730",
    ],
)
def test_malformed_links_are_refused(uri: str) -> None:
    with pytest.raises(UnsafeLinkError):
        RedirectLink(uri)


def test_mobile_link_is_checked_like_the_main_one() -> None:
    with pytest.raises(UnsafeLinkError):
        RedirectLink(STEAM, mobile="javascript:alert(1)")


@pytest.mark.parametrize("fallback", ["steam://store/730", "http://store.steampowered.com/", "javascript:alert(1)"])
def test_fallback_must_be_https(fallback: str) -> None:
    with pytest.raises(UnsafeLinkError):
        RedirectLink(STEAM, fallback=fallback)


def test_phones_open_the_mobile_link_when_there_is_one() -> None:
    link = RedirectLink(STEAM, mobile=STORE)
    assert link.target(phone=True) == STORE
    assert link.target(phone=False) == STEAM
    assert RedirectLink(STEAM).target(phone=True) == STEAM


def test_link_on_a_dashboard_round_trips_through_its_query() -> None:
    url = RedirectLink(STEAM, mobile=STORE, fallback=STORE).on("https://dash.example/")
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == f"https://dash.example{REDIRECT_PATH}"
    assert parse_qs(parts.query) == {"uri": [STEAM], "mobile": [STORE], "fallback": [STORE]}


def test_link_leaves_out_what_it_doesnt_have() -> None:
    assert parse_qs(urlsplit(RedirectLink(STEAM).on("https://dash.example")).query) == {"uri": [STEAM]}


# --- The page ---------------------------------------------------------------------------------------------------------


def test_the_page_opens_the_link_without_signing_in(client: TestClient) -> None:
    status, page = _redirect(client, uri=STEAM)
    assert status == 200
    assert f'window.location.href = "{STEAM}"' in page
    assert f'href="{STEAM}"' in page


def test_the_page_shows_the_fallback(client: TestClient) -> None:
    _, page = _redirect(client, uri=STEAM, fallback=STORE)
    assert f'href="{STORE}"' in page


def test_desktops_open_the_main_link(client: TestClient) -> None:
    _, page = _redirect(client, uri=STEAM, mobile=STORE)
    assert f'window.location.href = "{STEAM}"' in page


@pytest.mark.parametrize("user_agent", [PHONE_UA, "Mozilla/5.0 (Linux; Android 15; Pixel 9) Chrome/130.0 Mobile Safari/537.36"])
def test_phones_open_the_mobile_link(client: TestClient, user_agent: str) -> None:
    _, page = _redirect(client, user_agent, uri=STEAM, mobile=STORE)
    assert f'window.location.href = "{STORE}"' in page
    assert f'href="{STORE}"' in page


def test_the_mobile_client_hint_wins_over_the_user_agent(client: TestClient) -> None:
    response = client.get(
        REDIRECT_PATH,
        params={"uri": STEAM, "mobile": STORE},
        headers={"User-Agent": PHONE_UA, "Sec-CH-UA-Mobile": "?0"},
    )
    assert f'window.location.href = "{STEAM}"' in response.text


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"uri": ""},
        {"uri": "http://store.steampowered.com/app/730/"},
        {"uri": "javascript:alert(1)"},
        {"uri": STEAM, "mobile": "data:text/html,x"},
        {"uri": STEAM, "fallback": "steam://store/730"},
    ],
)
def test_refused_links_get_a_400_and_no_redirect(client: TestClient, query: dict[str, str]) -> None:
    status, page = _redirect(client, **query)
    assert status == 400
    assert "window.location" not in page


def test_the_page_escapes_the_link(client: TestClient) -> None:
    uri = 'steam://store/730"><script>alert(1)</script></'
    status, page = _redirect(client, uri=uri, fallback='https://example.com/"><img/src=x/onerror=alert(1)>')
    assert status == 200
    assert "<script>alert(1)" not in page
    assert "<img" not in page
    assert "</" not in page.split("window.location.href", 1)[1].split("\n", 1)[0]


@pytest.mark.parametrize("query", [{"uri": STEAM}, {"uri": "javascript:alert(1)"}])
def test_the_page_sets_no_cookie_and_sends_no_referrer(client: TestClient, query: dict[str, str]) -> None:
    response = client.get(REDIRECT_PATH, params=query)
    assert "set-cookie" not in response.headers
    assert response.headers["Referrer-Policy"] == "no-referrer"
