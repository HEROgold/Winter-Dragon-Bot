"""Unit tests: signing in reads the member's guilds, returns them to the page they came from and retries silently (no network)."""

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from wd_bot.application import ApplicationId
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_discord.testing import user_json

from winter_dragon.web import auth
from winter_dragon.web.app import create_app
from winter_dragon.web.discord_oauth import Granted
from winter_dragon.web.shared_guilds import SharedGuilds, safe_return_path


if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from sqlalchemy import Engine


USER = User.model_validate(user_json(id="42", username="frostbyte", global_name="Frost"))
BOT_GUILDS = frozenset({Snowflake(1), Snowflake(2)})
MEMBER_GUILDS = frozenset({Snowflake(2), Snowflake(3)})


class FakeLookup:
    """Stands in for :class:`~winter_dragon.web.discord_lookup.DiscordLookup`: the bot is in :data:`BOT_GUILDS`."""

    async def bot_guild_ids(self) -> frozenset[Snowflake] | None:
        return BOT_GUILDS


@pytest.fixture
def app_client(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(ApplicationId, "value", Snowflake(2))

    async def granted(code: str) -> Granted | None:
        return Granted(USER, MEMBER_GUILDS) if code == "granted" else None

    monkeypatch.setattr(auth, "signed_in_user", granted)
    app = create_app(bind=engine, session_secret="test-secret", lookup=FakeLookup())  # type: ignore[arg-type] - a stand-in
    return TestClient(app)


def query_of(response_location: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(response_location).query)


def test_login_asks_for_the_guilds_scope_silently(app_client: TestClient) -> None:
    login = app_client.get("/auth/discord/login", follow_redirects=False)

    query = query_of(login.headers["location"])
    assert query["scope"] == ["identify guilds"]
    assert query["prompt"] == ["none"]


def test_signing_in_keeps_the_guilds_the_member_and_the_bot_share(app_client: TestClient) -> None:
    login = app_client.get("/auth/discord/login", follow_redirects=False)
    state = query_of(login.headers["location"])["state"][0]

    app_client.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)

    shared = app_client.app.state.shared_guilds  # type: ignore[attr-defined] - set by create_app
    assert [guilds for _, guilds in shared._by_session.values()] == [frozenset({Snowflake(2)})]  # noqa: SLF001


def test_signing_in_returns_to_the_card_that_asked(app_client: TestClient) -> None:
    login = app_client.get("/auth/discord/login?next=/cards/user/7", follow_redirects=False)
    state = query_of(login.headers["location"])["state"][0]

    done = app_client.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)

    assert (done.status_code, done.headers["location"]) == (303, "/cards/user/7")


@pytest.mark.parametrize("target", ["https://evil.example/", "//evil.example/cards/user/1", "/cards\\evil", "/admin"])
def test_signing_in_never_returns_off_site(app_client: TestClient, target: str) -> None:
    login = app_client.get("/auth/discord/login", params={"next": target}, follow_redirects=False)
    state = query_of(login.headers["location"])["state"][0]

    done = app_client.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)

    assert done.headers["location"] == "/me"


def test_a_silent_sign_in_that_needs_the_member_falls_back_to_the_consent_page(app_client: TestClient) -> None:
    login = app_client.get("/auth/discord/login?next=/cards/guild/2", follow_redirects=False)
    state = query_of(login.headers["location"])["state"][0]

    retry = app_client.get(f"/auth/discord/callback?error=consent_required&state={state}", follow_redirects=False)

    query = query_of(retry.headers["location"])
    assert (retry.status_code, query["prompt"]) == (302, ["consent"])
    done = app_client.get(
        f"/auth/discord/callback?code=granted&state={query['state'][0]}",
        follow_redirects=False,
    )
    assert done.headers["location"] == "/cards/guild/2"


def test_a_refusal_with_a_forged_state_is_not_retried(app_client: TestClient) -> None:
    app_client.get("/auth/discord/login", follow_redirects=False)

    response = app_client.get("/auth/discord/callback?error=consent_required&state=forged", follow_redirects=False)

    assert response.status_code == 400


def test_signing_out_forgets_the_guilds(app_client: TestClient) -> None:
    login = app_client.get("/auth/discord/login", follow_redirects=False)
    state = query_of(login.headers["location"])["state"][0]
    app_client.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)
    page = app_client.get("/profile/reminders").text
    token = page.split('name="csrf_token" value="')[1].split('"')[0]

    app_client.post("/auth/logout", data={"csrf_token": token}, follow_redirects=False)

    assert not app_client.app.state.shared_guilds._by_session  # type: ignore[attr-defined]  # noqa: SLF001


class Clock:
    """A clock that moves when told to."""

    def __init__(self) -> None:
        from datetime import UTC, datetime

        self.moment = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.moment


def test_shared_guilds_go_stale_after_fifteen_minutes() -> None:
    from datetime import timedelta

    clock = Clock()
    shared = SharedGuilds(now=clock)
    shared.remember("session", frozenset({Snowflake(2)}))

    clock.moment += timedelta(minutes=14, seconds=59)
    assert shared.current("session") == frozenset({Snowflake(2)})
    clock.moment += timedelta(seconds=1)
    assert shared.current("session") is None
    assert shared.current(None) is None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/cards/user/7", "/cards/user/7"),
        ("/profile/teams", "/profile/teams"),
        (None, None),
        ("cards/user/7", None),
        ("/cards/user/7\r\nSet-Cookie: x", None),
    ],
)
def test_safe_return_path(path: str | None, expected: str | None) -> None:
    assert safe_return_path(path) == expected
