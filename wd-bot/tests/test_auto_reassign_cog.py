"""Unit tests: a member who leaves and rejoins gets their roles back, in guilds that turned it on (no network)."""

from typing import TYPE_CHECKING, Any

import pytest
from sqlmodel import Session
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import create_or_restore
from wd_db.testing import seed
from wd_discord import Member, MemberRemove, Permissions
from wd_discord.gateway import EventName, parse_dispatch, parse_ready
from wd_discord.testing import GUILD_JSON, RecordingClient, member_json, role_json, user_json

from winter_dragon.cogs.auto_reassign import AutoReassign, AutoReassignGuild, RememberedRole, is_enabled


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 7
MEMBER_ID = 3
BOT_ID = 42
BOT_ROLE = 50
"""The bot's own role: ranked above every role in these tests unless one says otherwise, and granting MANAGE_ROLES."""
USER = user_json(id=str(MEMBER_ID))
BOT_USER = user_json(id=str(BOT_ID), username="bot", bot=True)
MEMBER_PATH = f"/guilds/{GUILD_ID}/members/{MEMBER_ID}"


def _role(
    role_id: int, *, managed: bool = False, position: int = 1, permissions: Permissions = Permissions.none()
) -> dict[str, Any]:
    return role_json(
        id=str(role_id),
        name=f"role {role_id}",
        position=position,
        permissions=str(int(permissions)),
        managed=managed,
        mentionable=False,
    )


def _bot_role(permissions: Permissions = Permissions.MANAGE_ROLES) -> dict[str, Any]:
    return _role(BOT_ROLE, position=10, permissions=permissions)


def _member(*role_ids: int, user: dict[str, Any] = USER) -> dict[str, Any]:
    return member_json(user=user, roles=[str(role_id) for role_id in role_ids])


def _connect(
    client: RecordingClient, roles: list[dict[str, Any]], *member_role_ids: int, bot_role: dict[str, Any] | None = None
) -> None:
    """Have ``client`` connect as the bot and receive the guild, with the member holding ``member_role_ids``."""
    client.receive(parse_ready({"v": 10, "session_id": "s", "resume_gateway_url": "wss://x", "user": BOT_USER, "guilds": []}))
    data = {
        **GUILD_JSON,
        "id": str(GUILD_ID),
        "roles": [*roles, bot_role or _bot_role()],
        "large": False,
        "channels": [],
        "threads": [],
        "members": [_member(*member_role_ids), _member(BOT_ROLE, user=BOT_USER)],
        "voice_states": [],
        "presences": [],
    }
    client.receive(parse_dispatch(EventName.GUILD_CREATE, data))


def _leave(client: RecordingClient) -> MemberRemove:
    event = client.receive(parse_dispatch(EventName.GUILD_MEMBER_REMOVE, {"guild_id": str(GUILD_ID), "user": USER})).event
    assert isinstance(event, MemberRemove)
    return event


def _join(client: RecordingClient, *role_ids: int) -> Member:
    event = client.receive(parse_dispatch(EventName.GUILD_MEMBER_ADD, {**_member(*role_ids), "guild_id": str(GUILD_ID)})).event
    assert isinstance(event, Member)
    return event


def _given(client: RecordingClient) -> list[str] | None:
    """Return the roles the one PATCH of the member set, sorted; ``None`` when none was sent."""
    patches = client.requests_to("PATCH", MEMBER_PATH)
    assert len(patches) <= 1
    return None if not patches else sorted(patches[0].json["roles"])


def _cog(engine: Engine, client: RecordingClient) -> AutoReassign:
    return detached_cog(AutoReassign, engine=engine, client=client)


@pytest.fixture
def enabled(engine: Engine) -> None:
    seed(engine, AutoReassignGuild(id=GUILD_ID))


@pytest.mark.usefixtures("enabled")
async def test_a_rejoining_member_gets_their_roles_back_in_one_request(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8), _role(9)], 8, 9)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _given(client) == ["8", "9"]
    assert client.requests_to("PATCH", MEMBER_PATH)[0].headers is not None
    assert not [sent for sent in client.sent if sent.method == "PUT"]


@pytest.mark.usefixtures("enabled")
async def test_roles_the_member_got_on_joining_are_kept(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8), _role(11)], 8)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client, 11))  # e.g. a verification bot's role

    assert _given(client) == ["11", "8"]


async def test_a_guild_that_did_not_turn_it_on_gives_nothing_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8)], 8)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _given(client) is None


@pytest.mark.usefixtures("enabled")
async def test_managed_roles_and_roles_deleted_meanwhile_are_not_given_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8), _role(9), _role(10, managed=True)], 8, 9, 10)

    await cog.on_member_remove(_leave(client))
    client.receive(parse_dispatch(EventName.GUILD_ROLE_DELETE, {"guild_id": str(GUILD_ID), "role_id": "9"}))
    await cog.on_member_add(_join(client))

    assert _given(client) == ["8"]


@pytest.mark.usefixtures("enabled")
async def test_roles_above_the_bots_highest_are_not_given_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8), _role(12, position=20)], 8, 12)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _given(client) == ["8"]


@pytest.mark.usefixtures("enabled")
async def test_without_manage_roles_nothing_is_sent(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8)], 8, bot_role=_bot_role(Permissions.none()))

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _given(client) is None


@pytest.mark.usefixtures("enabled")
async def test_a_guild_the_client_does_not_know_is_fetched_first(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    seed(engine, *(RememberedRole(guild_id=GUILD_ID, user_id=MEMBER_ID, role_id=role_id) for role_id in (8, 12)))
    client.reply(
        "GET",
        f"/guilds/{GUILD_ID}",
        {**GUILD_JSON, "id": str(GUILD_ID), "roles": [_role(8), _role(12, position=20), _bot_role()]},
    )
    client.reply("GET", "/users/@me", BOT_USER)
    client.reply("GET", f"/guilds/{GUILD_ID}/members/{BOT_ID}", _member(BOT_ROLE, user=BOT_USER))
    client.reply("PATCH", MEMBER_PATH, _member(8))

    await cog.on_member_add(_join(client))

    assert _given(client) == ["8"]
    assert client.requests_to("GET", f"/guilds/{GUILD_ID}")


@pytest.mark.usefixtures("enabled")
async def test_nothing_to_give_back_sends_nothing(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(10, managed=True)], 10)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _given(client) is None


@pytest.mark.usefixtures("enabled")
async def test_leaving_again_remembers_only_the_latest_roles(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8), _role(9)], 8)
    await cog.on_member_remove(_leave(client))
    client.receive(parse_dispatch(EventName.GUILD_MEMBER_ADD, {**_member(9), "guild_id": str(GUILD_ID)}))

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _given(client) == ["9"]


def _enabled(engine: Engine) -> bool:
    with Session(engine) as session:
        return is_enabled(session, GUILD_ID)


async def test_enable_and_disable_turn_it_on_and_off(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = _cog(engine, discord_client)

    enable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
    await AutoReassign.enable.invoke(cog, enable, enable.options)
    assert _enabled(engine)

    disable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
    await AutoReassign.disable.invoke(cog, disable, disable.options)
    assert not _enabled(engine)


async def test_enable_warns_about_roles_above_the_bot(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _connect(discord_client, [_role(8), _role(12, position=20)], 8)
    enable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)

    await AutoReassign.enable.invoke(_cog(engine, discord_client), enable, enable.options)

    reply = discord_client.interaction_responses()[0]["data"]["content"]
    assert "<@&12>" in reply
    assert "<@&8>" not in reply


async def test_enable_warns_without_manage_roles(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _connect(discord_client, [_role(8)], 8, bot_role=_bot_role(Permissions.none()))
    enable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)

    await AutoReassign.enable.invoke(_cog(engine, discord_client), enable, enable.options)

    assert "Manage Roles" in discord_client.interaction_responses()[0]["data"]["content"]
    assert _enabled(engine)  # it still turns on; the warning says what to fix


async def test_enable_without_problems_gives_the_plain_hint(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    _connect(discord_client, [_role(8)], 8)
    enable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)

    await AutoReassign.enable.invoke(_cog(engine, discord_client), enable, enable.options)

    reply = discord_client.interaction_responses()[0]["data"]["content"]
    assert reply.startswith("Members who leave and rejoin now get their roles back")
    assert "<@&" not in reply


@pytest.mark.parametrize("command", [AutoReassign.enable, AutoReassign.disable])
async def test_enable_and_disable_need_manage_roles(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
    command: Any,
) -> None:
    seed(engine, AutoReassignGuild(id=GUILD_ID + 1))
    interaction = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_CHANNELS)

    await command.invoke(_cog(engine, discord_client), interaction, interaction.options)

    assert not _enabled(engine)
    assert discord_client.interaction_responses()[0]["data"]["content"] == "You need the Manage Roles permission for that."


@pytest.mark.usefixtures("enabled")
async def test_when_the_bots_rights_are_unknown_each_role_is_tried_on_its_own(engine: Engine) -> None:
    """One refused role in a single PATCH would lose them all, so without the bot's rights each goes out alone."""
    client = RecordingClient()
    cog = _cog(engine, client)
    seed(engine, *(RememberedRole(guild_id=GUILD_ID, user_id=MEMBER_ID, role_id=role_id) for role_id in (8, 9)))
    # No reply to GET /guilds/7: the guild can't be read, so the bot's rights can't be worked out.

    await cog.on_member_add(_join(client))

    assert _given(client) is None
    put = [sent.path.removeprefix(f"{MEMBER_PATH}/roles/") for sent in client.sent if sent.method == "PUT"]
    assert sorted(put) == ["8", "9"]


@pytest.mark.usefixtures("enabled")
async def test_a_fetched_guild_is_not_fetched_again(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    client.reply("GET", f"/guilds/{GUILD_ID}", {**GUILD_JSON, "id": str(GUILD_ID), "roles": [_role(8), _bot_role()]})
    client.reply("GET", "/users/@me", BOT_USER)
    client.reply("GET", f"/guilds/{GUILD_ID}/members/{BOT_ID}", _member(BOT_ROLE, user=BOT_USER))
    client.reply("PATCH", MEMBER_PATH, _member(8))
    for _ in range(2):
        with Session(engine) as session:
            create_or_restore(session, RememberedRole(guild_id=GUILD_ID, user_id=MEMBER_ID, role_id=8))
            session.commit()
        await cog.on_member_add(_join(client))

    assert len(client.requests_to("GET", f"/guilds/{GUILD_ID}")) == 1
    assert len(client.requests_to("GET", f"/guilds/{GUILD_ID}/members/{BOT_ID}")) == 1


async def test_enable_disable_enable_leaves_it_on(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = _cog(engine, discord_client)

    for command in (AutoReassign.enable, AutoReassign.disable, AutoReassign.enable):
        interaction = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
        await command.invoke(cog, interaction, interaction.options)

    assert _enabled(engine)
    responses = [response["data"]["content"] for response in discord_client.interaction_responses()]
    assert responses[1] == "Rejoining members no longer get their roles back."
    assert all(response.startswith("Members who leave and rejoin now get their roles back") for response in responses[::2])


@pytest.mark.usefixtures("enabled")
async def test_after_disable_nothing_comes_back_and_after_enable_again_it_does(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    client = RecordingClient()
    listener, commands = _cog(engine, client), _cog(engine, discord_client)
    _connect(client, [_role(8)], 8)
    await listener.on_member_remove(_leave(client))

    disable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
    await AutoReassign.disable.invoke(commands, disable, disable.options)
    await listener.on_member_add(_join(client, 8))
    assert _given(client) is None

    enable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
    await AutoReassign.enable.invoke(commands, enable, enable.options)
    await listener.on_member_remove(_leave(client))
    await listener.on_member_add(_join(client))
    assert _given(client) == ["8"]


@pytest.mark.usefixtures("enabled")
async def test_roles_given_back_and_forgotten_never_come_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _connect(client, [_role(8), _role(9)], 8, 9)
    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))
    client.receive(
        parse_dispatch(EventName.GUILD_MEMBER_UPDATE, {**_member(9), "avatar": None, "banner": None, "guild_id": str(GUILD_ID)})
    )

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    first, second = client.requests_to("PATCH", MEMBER_PATH)
    assert (sorted(first.json["roles"]), second.json["roles"]) == (["8", "9"], ["9"])
