"""Unit tests: the web dashboard's sign-in, data page, deletion request and reminders, on sqlite (no network)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select
from wd_bot.application import ApplicationId
from wd_db.extension.lifecycle import alive
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake

from winter_dragon.cogs import import_cogs
from winter_dragon.cogs.reminder import Reminder, TimedReminder
from winter_dragon.web import auth, pages, reminders
from winter_dragon.web.app import create_app
from winter_dragon.web.reminders import InvalidReminderError, ReminderDraft, Repeat


if TYPE_CHECKING:
    from sqlalchemy import Engine


NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
ZONE = "Europe/Amsterdam"
"""UTC+2 on :data:`NOW`."""
MEMBER_ID = 42
OTHER_ID = 7
USER = User.model_validate({"id": str(MEMBER_ID), "username": "frostbyte", "discriminator": "0", "global_name": "Frost"})
HTMX = {"HX-Request": "true"}
CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture
def bind(engine: Engine) -> Engine:
    """Return the test database with the table of every cog, as the dashboard knows them all."""
    import_cogs()
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(bind: Engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Return a browser on the dashboard at :data:`NOW`, in :data:`ZONE`, not signed in."""
    monkeypatch.setattr(ApplicationId, "value", Snowflake(2))
    monkeypatch.setattr(reminders, "utc_now", lambda: NOW)
    monkeypatch.setattr(pages, "utc_now", lambda: NOW)
    browser = TestClient(create_app(bind=bind, session_secret="test-secret"))
    browser.cookies.set("tz", ZONE)
    return browser


def _sign_in(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def granted(code: str) -> User | None:
        return USER if code == "granted" else None

    monkeypatch.setattr(auth, "signed_in_user", granted)
    login = client.get("/auth/discord/login", follow_redirects=False)
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    client.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)


@pytest.fixture
def member(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Return the browser signed in as :data:`USER`."""
    _sign_in(client, monkeypatch)
    return client


def _csrf(client: TestClient) -> str:
    match = CSRF.search(client.get("/reminders").text)
    assert match is not None
    return match.group(1)


def _seed(bind: Engine, *rows: Reminder | TimedReminder) -> list[int]:
    with Session(bind) as session:
        session.add_all(rows)
        session.commit()
        return [row.id for row in rows if row.id is not None]


def _alive_contents(bind: Engine) -> list[str]:
    with Session(bind) as session:
        once = [row.content for row in session.exec(alive(Reminder))]
        return once + [row.content for row in session.exec(alive(TimedReminder))]


# --- Signing in -------------------------------------------------------------------------------------------------------


def test_the_landing_page_lists_every_command_group(client: TestClient) -> None:
    page = client.get("/").text

    assert "/reminder" in page
    assert "/steam" in page
    assert 'href="/auth/discord/login"' in page


def test_the_signpost_says_what_a_member_will_find(client: TestClient, bind: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(
        bind,
        Reminder(content="mine", user_id=MEMBER_ID, timestamp=NOW + timedelta(hours=1)),
        TimedReminder(content="daily", user_id=MEMBER_ID, timestamp=NOW, repeat_every=timedelta(days=1)),
        Reminder(content="theirs", user_id=OTHER_ID, timestamp=NOW + timedelta(hours=1)),
    )
    assert 'class="arm-time"' not in client.get("/").text

    _sign_in(client, monkeypatch)
    page = client.get("/").text

    assert "2 reminders" in page
    assert "2 entries" in page


def test_a_page_that_needs_sign_in_sends_you_to_sign_in(client: TestClient) -> None:
    page = client.get("/me", follow_redirects=False)
    fragment = client.get("/me", headers=HTMX, follow_redirects=False)

    assert (page.status_code, page.headers["location"]) == (303, "/auth/discord/login")
    assert (fragment.status_code, fragment.headers["HX-Redirect"]) == (401, "/auth/discord/login")


def test_signing_in_needs_the_state_it_was_sent_with(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def never(_code: str) -> User | None:
        pytest.fail("a forged callback must not reach Discord")

    monkeypatch.setattr(auth, "signed_in_user", never)
    client.get("/auth/discord/login", follow_redirects=False)

    response = client.get("/auth/discord/callback?code=granted&state=forged", follow_redirects=False)

    assert response.status_code == 400
    assert client.get("/me", follow_redirects=False).status_code == 303


def test_signing_in_opens_your_data_page_and_signing_out_ends_it(member: TestClient) -> None:
    page = member.get("/me").text
    assert "Frost" in page
    assert f"Discord ID {MEMBER_ID}" in page

    member.post("/auth/logout", data={"csrf_token": _csrf(member)}, follow_redirects=False)

    assert member.get("/me", follow_redirects=False).status_code == 303


# --- Your data --------------------------------------------------------------------------------------------------------


def test_the_data_page_lists_only_what_the_bot_stores_about_you(member: TestClient, bind: Engine) -> None:
    _seed(
        bind,
        Reminder(content="mine", user_id=MEMBER_ID, timestamp=NOW + timedelta(hours=19)),
        Reminder(content="theirs", user_id=OTHER_ID, timestamp=NOW + timedelta(hours=1)),
    )

    page = member.get("/me").text
    rows = member.get("/me/records/reminder", headers=HTMX).text

    assert "1 entry" in page
    assert "mine" in rows
    assert "theirs" not in rows
    assert "9 Oct 2026, 09:00" in rows  # 07:00 UTC, in Amsterdam


def test_a_record_that_does_not_exist_is_not_found(member: TestClient) -> None:
    assert member.get("/me/records/nonsense").status_code == 404


def test_deleting_your_data_needs_your_username(member: TestClient, bind: Engine) -> None:
    _seed(bind, Reminder(content="mine", user_id=MEMBER_ID, timestamp=NOW + timedelta(days=1)))

    response = member.post("/me/deletion", data={"csrf_token": _csrf(member), "confirm_name": "Frost"}, headers=HTMX)

    assert response.status_code == 422
    assert "Type frostbyte exactly" in response.text
    assert _alive_contents(bind) == ["mine"]


def test_deleting_your_data_hides_it_and_shows_how_far_it_got(member: TestClient, bind: Engine) -> None:
    _seed(
        bind,
        Reminder(content="mine", user_id=MEMBER_ID, timestamp=NOW + timedelta(days=1)),
        Reminder(content="theirs", user_id=OTHER_ID, timestamp=NOW + timedelta(days=1)),
    )

    response = member.post("/me/deletion", data={"csrf_token": _csrf(member), "confirm_name": "frostbyte"}, headers=HTMX)

    assert response.status_code == 200
    assert "Deletion requested" in response.text
    assert "stores nothing about you" in response.text
    assert _alive_contents(bind) == ["theirs"]
    assert "Deletion requested" in member.get("/me").text


# --- Reminders --------------------------------------------------------------------------------------------------------


def test_adding_a_reminder_stores_it_due_at_the_time_in_your_zone(member: TestClient, bind: Engine) -> None:
    response = member.post(
        "/reminders",
        data={"csrf_token": _csrf(member), "content": "Water the plants", "day": "2026-10-09", "at": "09:00"},
        headers=HTMX,
    )

    assert response.status_code == 200
    assert "Tomorrow" in response.text
    with Session(bind) as session:
        stored = session.exec(select(Reminder)).one()
    assert (stored.content, stored.user_id) == ("Water the plants", MEMBER_ID)
    assert stored.timestamp.astimezone(UTC) == datetime(2026, 10, 9, 7, 0, tzinfo=UTC)


def test_a_reminder_can_repeat_every_few_days(member: TestClient, bind: Engine) -> None:
    response = member.post(
        "/reminders",
        data={
            "csrf_token": _csrf(member),
            "content": "Water the plants",
            "day": "2026-10-09",
            "at": "09:00",
            "repeat": Repeat.EVERY_DAYS,
            "every_days": "3",
        },
        headers=HTMX,
    )

    assert "Every 3 days" in response.text
    with Session(bind) as session:
        assert session.exec(select(TimedReminder)).one().repeat_every == timedelta(days=3)


def test_a_reminder_in_the_past_is_refused_and_the_form_kept(member: TestClient, bind: Engine) -> None:
    response = member.post(
        "/reminders",
        data={"csrf_token": _csrf(member), "content": "Too late", "day": "2026-10-08", "at": "09:00"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "Pick a time between now and" in response.text
    assert "Too late" in response.text
    assert _alive_contents(bind) == []


def test_a_form_without_the_csrf_token_is_refused(member: TestClient, bind: Engine) -> None:
    response = member.post("/reminders", data={"content": "Forged", "day": "2026-10-09", "at": "09:00"}, headers=HTMX)

    assert response.status_code == 403
    assert _alive_contents(bind) == []


def test_without_htmx_a_form_redirects_back_to_its_page(member: TestClient) -> None:
    response = member.post(
        "/reminders",
        data={"csrf_token": _csrf(member), "content": "Plain form", "day": "2026-10-09", "at": "09:00"},
        follow_redirects=False,
    )

    assert (response.status_code, response.headers["location"]) == (303, "/reminders")


def test_you_can_only_delete_your_own_reminders(member: TestClient, bind: Engine) -> None:
    mine, theirs = _seed(
        bind,
        Reminder(content="mine", user_id=MEMBER_ID, timestamp=NOW + timedelta(days=1)),
        Reminder(content="theirs", user_id=OTHER_ID, timestamp=NOW + timedelta(days=1)),
    )
    token = _csrf(member)

    member.post(f"/reminders/once:{theirs}/delete", data={"csrf_token": token}, headers=HTMX)
    assert sorted(_alive_contents(bind)) == ["mine", "theirs"]

    response = member.post(f"/reminders/once:{mine}/delete", data={"csrf_token": token}, headers=HTMX)
    assert _alive_contents(bind) == ["theirs"]
    assert "No reminders coming up" in response.text


@pytest.mark.parametrize(
    ("draft", "why"),
    [
        (ReminderDraft(content="  ", day="2026-10-09"), "Write what to remind you of"),
        (ReminderDraft(content="x" * 5000, day="2026-10-09"), "Keep your reminder under"),
        (ReminderDraft(content="x", day="not a day"), "Pick a date and a time"),
        (ReminderDraft(content="x", day="2026-10-09", repeat=Repeat.EVERY_DAYS, every_days="0"), "Repeat every 1 to"),
    ],
)
def test_a_draft_that_cannot_be_a_reminder_says_why(draft: ReminderDraft, why: str) -> None:
    with pytest.raises(InvalidReminderError, match=why):
        draft.reminder(MEMBER_ID, ZoneInfo(ZONE), NOW)
