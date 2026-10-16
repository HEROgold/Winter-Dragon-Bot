"""Unit tests: a member who leaves and rejoins gets their roles back, in guilds that turned it on (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from sqlmodel import Session
from wd_bot.registry import CommandRegistry
from wd_discord import Member, MemberRemove, Permissions
from wd_discord.gateway import EventName, parse_dispatch
from wd_discord.testing import GUILD_JSON, RecordingClient

from winter_dragon.cogs.auto_reassign import AutoReassign, AutoReassignGuild, is_enabled


if TYPE_CHECKING:
    from conftest import InteractionFactory
    from sqlalchemy import Engine


GUILD_ID = 7
MEMBER_ID = 3
USER = {"id": str(MEMBER_ID), "username": "someone", "discriminator": "0"}


def _role(role_id: int, *, managed: bool = False) -> dict[str, Any]:
    return {
        "id": str(role_id),
        "name": f"role {role_id}",
        "color": 0,
        "hoist": False,
        "position": 1,
        "permissions": "0",
        "managed": managed,
        "mentionable": False,
        "flags": 0,
    }


def _member(*role_ids: int) -> dict[str, Any]:
    return {"user": USER, "roles": [str(role_id) for role_id in role_ids], "joined_at": None, "deaf": False, "mute": False}


def _guild_create(client: RecordingClient, roles: list[dict[str, Any]], *member_role_ids: int) -> None:
    data = {
        **GUILD_JSON,
        "id": str(GUILD_ID),
        "roles": roles,
        "large": False,
        "channels": [],
        "threads": [],
        "members": [_member(*member_role_ids)],
        "voice_states": [],
        "presences": [],
    }
    client.receive(parse_dispatch(EventName.GUILD_CREATE, data))


def _leave(client: RecordingClient) -> MemberRemove:
    event = client.receive(parse_dispatch(EventName.GUILD_MEMBER_REMOVE, {"guild_id": str(GUILD_ID), "user": USER})).event
    assert isinstance(event, MemberRemove)
    return event


def _join(client: RecordingClient) -> Member:
    event = client.receive(parse_dispatch(EventName.GUILD_MEMBER_ADD, {**_member(), "guild_id": str(GUILD_ID)})).event
    assert isinstance(event, Member)
    return event


def _readded(client: RecordingClient) -> list[str]:
    prefix = f"/guilds/{GUILD_ID}/members/{MEMBER_ID}/roles/"
    return [
        request.path.removeprefix(prefix)
        for request in client.sent
        if request.method == "PUT" and request.path.startswith(prefix)
    ]


def _cog(engine: Engine, client: RecordingClient) -> AutoReassign:
    cog = AutoReassign.__new__(AutoReassign)
    cog.bot = SimpleNamespace(client=client, registry=CommandRegistry())  # pyright: ignore[reportAttributeAccessIssue]
    cog.session = Session(engine)
    return cog


@pytest.fixture
def enabled(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(AutoReassignGuild(guild_id=GUILD_ID))
        session.commit()


@pytest.mark.usefixtures("enabled")
async def test_a_rejoining_member_gets_their_roles_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _guild_create(client, [_role(8), _role(9)], 8, 9)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert sorted(_readded(client)) == ["8", "9"]


async def test_a_guild_that_did_not_turn_it_on_gives_nothing_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _guild_create(client, [_role(8)], 8)

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _readded(client) == []


@pytest.mark.usefixtures("enabled")
async def test_managed_roles_and_roles_deleted_meanwhile_are_not_given_back(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _guild_create(client, [_role(8), _role(9), _role(10, managed=True)], 8, 9, 10)

    await cog.on_member_remove(_leave(client))
    client.receive(parse_dispatch(EventName.GUILD_ROLE_DELETE, {"guild_id": str(GUILD_ID), "role_id": "9"}))
    await cog.on_member_add(_join(client))

    assert _readded(client) == ["8"]


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


@pytest.mark.parametrize("command", [AutoReassign.enable, AutoReassign.disable])
async def test_enable_and_disable_need_manage_roles(
    engine: Engine,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
    command: Any,
) -> None:
    with Session(engine) as session:
        session.add(AutoReassignGuild(guild_id=GUILD_ID + 1))
        session.commit()
    interaction = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_CHANNELS)

    await command.invoke(_cog(engine, discord_client), interaction, interaction.options)

    assert not _enabled(engine)
    assert discord_client.interaction_responses()[0]["data"]["content"] == "You need the Manage Roles permission for that."


@pytest.mark.usefixtures("enabled")
async def test_leaving_again_remembers_only_the_latest_roles(engine: Engine) -> None:
    client = RecordingClient()
    cog = _cog(engine, client)
    _guild_create(client, [_role(8), _role(9)], 8)
    await cog.on_member_remove(_leave(client))
    client.receive(parse_dispatch(EventName.GUILD_MEMBER_ADD, {**_member(9), "guild_id": str(GUILD_ID)}))

    await cog.on_member_remove(_leave(client))
    await cog.on_member_add(_join(client))

    assert _readded(client) == ["9"]
