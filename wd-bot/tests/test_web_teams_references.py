"""Unit tests: the teams page shows people as reference links, and no page can print a Discord ID (no network)."""

import dataclasses
import html
from datetime import UTC, datetime
import importlib
import pkgutil
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel
from wd_bot.application import ApplicationId
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient, user_json

from winter_dragon.cogs import import_cogs
from winter_dragon.cogs.team.models import TeamKind
from winter_dragon.web import auth, profile_pages
from winter_dragon.web.app import create_app
from winter_dragon.web.discord_lookup import DiscordLookup
from winter_dragon.web.discord_oauth import Granted
from winter_dragon.web.references import ReferenceLink
from winter_dragon.web.responses import TEMPLATES_DIR


IRONCLAD = "Ironclad"
MEMBER_ID = 42
VIEWER = User.model_validate(user_json(id=str(MEMBER_ID), username="frostbyte", global_name="Frost"))
STRANGER = "77"
GONE = 99
UNKNOWN_USER = {"code": 10013, "message": "Unknown User"}
NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def sign_in(browser: TestClient) -> None:
    login = browser.get("/auth/discord/login", follow_redirects=False)
    state = login.headers["location"].split("state=")[1].split("&")[0]
    browser.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)


def _team(bind, name: str, kind: TeamKind, member_ids: tuple[int, ...], *, captain_id: int | None) -> None:  # noqa: ANN001
    from winter_dragon.cogs.team.models import Team, TeamMember, TeamOrigin

    team = Team(name=name, kind=kind, origin=TeamOrigin.CREATED, captain_id=captain_id)
    with Session(bind) as session:
        session.add(team)
        session.commit()
        session.refresh(team)
        assert team.id is not None
        session.add_all(TeamMember(team_id=team.id, user_id=member, joined_at=NOW) for member in member_ids)
        session.commit()


@pytest.fixture
def discord() -> RecordingClient:
    client = RecordingClient()
    client.reply("GET", "/users/@me/guilds", [])
    client.reply("GET", f"/users/{MEMBER_ID}", user_json(id=str(MEMBER_ID), username="frostbyte", global_name="Frost"))
    client.reply("GET", f"/users/{STRANGER}", user_json(id=STRANGER, username="stranger", global_name="Stranger"))
    client.reply("GET", f"/users/{GONE}", UNKNOWN_USER, status=404)
    return client


@pytest.fixture
def member(engine, monkeypatch: pytest.MonkeyPatch, discord: RecordingClient) -> TestClient:  # noqa: ANN001
    import_cogs()
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(ApplicationId, "value", Snowflake(2))

    async def granted(code: str) -> Granted | None:
        return Granted(VIEWER, frozenset()) if code == "granted" else None

    monkeypatch.setattr(auth, "signed_in_user", granted)
    lookup = DiscordLookup("token")
    lookup._client = discord  # noqa: SLF001 - skip opening a real connection
    browser = TestClient(create_app(bind=engine, session_secret="test-secret", lookup=lookup))
    sign_in(browser)
    return browser


def test_captain_and_members_link_to_their_cards_by_name(member: TestClient, engine) -> None:  # noqa: ANN001
    _team(engine, IRONCLAD, TeamKind.LASTING, (MEMBER_ID, int(STRANGER)), captain_id=int(STRANGER))

    page = member.get("/profile/teams").text

    assert f'<a href="/cards/user/{STRANGER}">Stranger</a>' in page
    assert f'<a href="/cards/user/{MEMBER_ID}">Frost</a>' in page
    assert f">{STRANGER}<" not in page


def test_a_deleted_user_shows_as_a_plain_id_with_a_note(member: TestClient, engine) -> None:  # noqa: ANN001
    _team(engine, IRONCLAD, TeamKind.LASTING, (MEMBER_ID, GONE), captain_id=MEMBER_ID)

    response = member.get("/profile/teams")

    assert response.status_code == 200
    page = html.unescape(response.text)
    assert "99" in page
    assert "Not found on Discord." in page
    assert "/cards/user/99" not in page


def test_discord_being_down_still_shows_the_page_with_the_ids(member: TestClient, engine, discord: RecordingClient) -> None:  # noqa: ANN001
    discord.reply("GET", f"/users/{STRANGER}", {"code": 0, "message": "Service unavailable"}, status=503)
    _team(engine, IRONCLAD, TeamKind.LASTING, (MEMBER_ID, int(STRANGER)), captain_id=MEMBER_ID)

    response = member.get("/profile/teams")

    assert response.status_code == 200
    assert "Couldn't load the name right now." in html.unescape(response.text)
    assert STRANGER in response.text


# --- Guards: a page can't print a Discord ID ----------------------------------------------------------------------

ID_NAMES = re.compile(r"\b(captain_ids?|member_ids?|user_ids?|channel_ids?|role_ids?|guild_ids?|target_ids?)\b")


def test_no_template_prints_a_discord_id_field() -> None:
    printing = [
        f"{path.relative_to(TEMPLATES_DIR)}:{number}: {line.strip()}"
        for path in TEMPLATES_DIR.rglob("*.html")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if ID_NAMES.search(line)
    ]

    assert not printing, "Show a Discord ID through a reference link (winter_dragon.web.references), not by its field:\n" + "\n".join(printing)


def _profile_page_dataclasses() -> list[type]:
    classes: list[type] = []
    for module_info in pkgutil.iter_modules(profile_pages.__path__):
        module = importlib.import_module(f"{profile_pages.__name__}.{module_info.name}")
        classes.extend(
            value
            for value in vars(module).values()
            if isinstance(value, type) and dataclasses.is_dataclass(value) and value.__module__ == module.__name__
        )
    return classes


def test_no_profile_page_row_holds_a_bare_snowflake() -> None:
    bare = [
        f"{row.__module__}.{row.__name__}.{field.name}"
        for row in _profile_page_dataclasses()
        for field in dataclasses.fields(row)
        if "Snowflake" in str(field.type)
    ]

    assert not bare, "A page row hands its template a bare Discord ID; hold a ReferenceLink instead:\n" + "\n".join(bare)


def test_the_teams_page_rows_hold_reference_links() -> None:
    from winter_dragon.web.profile_pages.teams import TeamRow

    kinds = {field.name: str(field.type) for field in dataclasses.fields(TeamRow)}

    assert "ReferenceLink" in kinds["captain"]
    assert "ReferenceLink" in kinds["members"]
    assert ReferenceLink  # the row type the template macro renders
    assert Path(TEMPLATES_DIR / "_references.html").exists()
