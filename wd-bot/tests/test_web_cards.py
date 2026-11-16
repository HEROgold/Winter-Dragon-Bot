"""Unit tests: the card pages, on the real name lookup over a recording Discord client (no network)."""

import html

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from wd_bot.application import ApplicationId
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_discord.testing import RecordingClient, channel_json, member_json, role_json, user_json
from wd_discord.testing.payloads import GUILD_JSON

from winter_dragon.cogs import import_cogs
from winter_dragon.web import auth
from winter_dragon.web.app import create_app
from winter_dragon.web.discord_lookup import DiscordLookup
from winter_dragon.web.discord_oauth import Granted
from winter_dragon.web.cards import NO_SUCH_CARD


VIEWER = User.model_validate(user_json(id="42", username="frostbyte", global_name="Frost"))
SHARED = Snowflake(7)
OTHER_GUILD = Snowflake(9)
STRANGER = "77"
OWNER = "11"
UNKNOWN_USER = {"code": 10013, "message": "Unknown User"}
UNKNOWN_MEMBER = {"code": 10007, "message": "Unknown Member"}


def listed(guild_id: int) -> dict[str, object]:
    return {"id": str(guild_id), "name": f"guild {guild_id}", "owner": False, "permissions": "0", "features": []}


@pytest.fixture
def discord() -> RecordingClient:
    client = RecordingClient()
    client.reply("GET", "/users/@me/guilds", [listed(7)])
    client.reply("GET", "/guilds/7", {**GUILD_JSON, "id": "7", "name": "Frost Guild", "owner_id": OWNER})
    client.reply("GET", "/guilds/7/roles", [role_json(id="7", name="@everyone", permissions="1024"), role_json()])
    client.reply("GET", "/users/42/guilds", [listed(7)])
    client.reply("GET", f"/users/{STRANGER}", user_json(id=STRANGER, username="stranger", global_name="Stranger"))
    client.reply("GET", "/guilds/7/members/42", member_json(user=user_json(id="42")))
    client.reply("GET", f"/guilds/7/members/{STRANGER}", member_json(user=user_json(id=STRANGER)))
    client.reply("GET", "/channels/5", channel_json(id="5", name="general", topic="Talk here"))
    return client


@pytest.fixture
def lookup(discord: RecordingClient) -> DiscordLookup:
    lookup = DiscordLookup("token")
    lookup._client = discord  # noqa: SLF001 - skip opening a real connection
    return lookup


@pytest.fixture
def browser(engine, monkeypatch: pytest.MonkeyPatch, lookup: DiscordLookup) -> TestClient:  # noqa: ANN001
    import_cogs()
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(ApplicationId, "value", Snowflake(2))

    async def granted(code: str) -> Granted | None:
        return Granted(VIEWER, frozenset({SHARED, OTHER_GUILD})) if code == "granted" else None

    monkeypatch.setattr(auth, "signed_in_user", granted)
    return TestClient(create_app(bind=engine, session_secret="test-secret", lookup=lookup))


def sign_in(browser: TestClient, *, next_path: str = "/me") -> None:
    login = browser.get("/auth/discord/login", params={"next": next_path}, follow_redirects=False)
    state = login.headers["location"].split("state=")[1].split("&")[0]
    browser.get(f"/auth/discord/callback?code=granted&state={state}", follow_redirects=False)


@pytest.fixture
def member(browser: TestClient) -> TestClient:
    sign_in(browser)
    return browser


def test_a_card_needs_a_signed_in_member(browser: TestClient) -> None:
    response = browser.get("/cards/guild/7", follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/auth/discord/login")


def test_a_guild_the_member_shares_with_the_bot_has_a_card(member: TestClient) -> None:
    page = member.get("/cards/guild/7")

    assert page.status_code == 200
    assert "Frost Guild" in page.text


def test_a_guild_the_bot_is_not_in_has_no_card(member: TestClient) -> None:
    page = member.get("/cards/guild/9")

    assert page.status_code == 404
    assert NO_SUCH_CARD in html.unescape(page.text)


def test_stale_guilds_send_the_member_through_a_silent_sign_in_and_back(member: TestClient) -> None:
    member.app.state.shared_guilds._by_session.clear()  # type: ignore[attr-defined]  # noqa: SLF001

    response = member.get("/cards/guild/7", follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/auth/discord/login?next=/cards/guild/7")


def test_a_member_opens_their_own_card(member: TestClient) -> None:
    client = member.app.state.lookup.client  # type: ignore[attr-defined]
    client.reply("GET", "/users/42", user_json(id="42", username="frostbyte", global_name="Frost"))

    page = member.get("/cards/user/42")

    assert page.status_code == 200
    assert "Frost" in page.text


def test_someone_who_shares_a_guild_has_a_card(member: TestClient) -> None:
    page = member.get(f"/cards/user/{STRANGER}")

    assert page.status_code == 200
    assert "Stranger" in page.text


def test_someone_in_none_of_your_guilds_has_the_same_page_as_an_unknown_id(
    member: TestClient,
    discord: RecordingClient,
) -> None:
    discord.reply("GET", f"/guilds/7/members/{STRANGER}", UNKNOWN_MEMBER, status=404)
    discord.reply("GET", "/users/99", UNKNOWN_USER, status=404)
    discord.reply("GET", "/guilds/7/members/99", UNKNOWN_MEMBER, status=404)

    hidden = member.get(f"/cards/user/{STRANGER}")
    unknown = member.get("/cards/user/99")

    assert (hidden.status_code, unknown.status_code) == (404, 404)
    assert hidden.text == unknown.text


def test_a_role_card_shows_the_role_and_links_its_guild(member: TestClient) -> None:
    page = member.get("/cards/role/7/8")

    assert page.status_code == 200
    assert "mods" in page.text
    assert 'href="/cards/guild/7"' in page.text


def test_a_role_of_a_guild_you_do_not_share_has_no_card(member: TestClient) -> None:
    assert member.get("/cards/role/9/8").status_code == 404


def test_a_channel_card_opens_when_the_member_could_see_it(member: TestClient) -> None:
    page = member.get("/cards/channel/5")

    assert page.status_code == 200
    assert "general" in page.text
    assert "Talk here" in page.text


def test_a_channel_hidden_from_the_member_has_no_card(member: TestClient, discord: RecordingClient) -> None:
    hidden = {"id": "7", "type": 0, "allow": "0", "deny": "1024"}
    discord.reply("GET", "/channels/5", channel_json(id="5", name="staff", permission_overwrites=[hidden]))

    assert member.get("/cards/channel/5").status_code == 404


def test_a_channel_outside_your_shared_guilds_has_no_card(member: TestClient, discord: RecordingClient) -> None:
    discord.reply("GET", "/channels/5", channel_json(id="5", guild_id="9"))

    assert member.get("/cards/channel/5").status_code == 404


def test_a_card_says_so_when_discord_does_not_answer(member: TestClient, discord: RecordingClient) -> None:
    discord.reply("GET", f"/users/{STRANGER}", {"code": 0, "message": "Service unavailable"}, status=503)

    page = member.get(f"/cards/user/{STRANGER}")

    assert page.status_code == 503
    assert "Discord didn't answer" in html.unescape(page.text)
