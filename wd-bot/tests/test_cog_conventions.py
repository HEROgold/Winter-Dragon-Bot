"""Behaviour tests: every live cog refuses, confirms and checks permissions the same way (no network).

A refused action answers the member privately with its reason as plain text, and nothing else; a successful
create, change or delete answers with the matching confirmation embed; a command needing a permission refuses a
member without it before acting.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from wd_bot.testing import detached_cog
from wd_db.testing import seed
from wd_discord.gateway.events import InteractionDataOption
from wd_discord.permissions import Permissions
from wd_discord.testing import RecordingClient, message_json
from wd_types.clock import utc_now

from winter_dragon.cogs.auto_reassign import AutoReassign, AutoReassignGuild
from winter_dragon.cogs.autochannel import AutoChannels
from winter_dragon.cogs.fuel import Fuel
from winter_dragon.cogs.invite import Invite
from winter_dragon.cogs.reminder.cog import Reminders
from winter_dragon.cogs.steam.cog import SteamSales
from winter_dragon.cogs.steam.models import SteamUsers
from winter_dragon.cogs.tournament.cog import Tournaments
from winter_dragon.cogs.urban import Urban, UrbanSettings
from winter_dragon.config import Settings


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine
    from wd_bot.cogs import GroupCog


EPHEMERAL = 1 << 6
GUILD_ID = 7
ASKER_ID = 3


@dataclass
class World:
    """What a scenario may use: the database, the command and button builders, and monkeypatch for settings."""

    engine: Engine
    command: InteractionFactory
    button: ComponentInteractionFactory
    monkeypatch: pytest.MonkeyPatch

    def cog[C](self, cls: type[C]) -> C:
        """Return ``cls`` on this world's database, with a client that accepts DMs."""
        client = RecordingClient()
        client.reply("POST", "/users/@me/channels", {"id": "6", "type": 1})
        client.reply("POST", "/channels/6/messages", message_json())
        return detached_cog(cls, engine=self.engine, client=client)


type Scenario = Callable[[World], Awaitable[None]]


def _options(**values: float | str) -> list[InteractionDataOption]:
    kinds = {str: 3, int: 4, float: 10}
    return [InteractionDataOption(name=name, type=kinds[type(value)], value=value) for name, value in values.items()]


async def _run(world: World, cls: type, command: Any, name: str, **options: float | str) -> None:
    """Invoke ``/name`` ``command`` of a fresh ``cls`` with ``options``, from a DM."""
    given = _options(**options)
    await command.invoke(world.cog(cls), world.command(name, options=given), given)


# --- Refusals --------------------------------------------------------------------------------------------------------


async def _fuel_nothing_spent(world: World) -> None:
    await _run(world, Fuel, Fuel.add, "fuel", price=0.0, distance=600.0, amount=40.0)


async def _fuel_date_to_come(world: World) -> None:
    await _run(world, Fuel, Fuel.add, "fuel", price=70.0, distance=600.0, amount=40.0, date="2999-01-01")


async def _fuel_no_refuels(world: World) -> None:
    await _run(world, Fuel, Fuel.efficiency, "fuel")


async def _invite_no_support_guild(world: World) -> None:
    world.monkeypatch.setattr(Settings, "support_guild_id", 0)
    await _run(world, Invite, Invite.support_invite, "invite")


async def _reminder_no_time(world: World) -> None:
    await _run(world, Reminders, Reminders.add, "reminder", reminder="water the plants")


async def _reminder_unknown(world: World) -> None:
    await _run(world, Reminders, Reminders.remove, "reminder", reminder="nothing like this")


async def _steam_already_subscribed(world: World) -> None:
    seed(world.engine, SteamUsers(id=ASKER_ID, sale_threshold=100, last_notification=utc_now()))
    await _run(world, SteamSales, SteamSales.add, "steam")


async def _steam_not_subscribed(world: World) -> None:
    await _run(world, SteamSales, SteamSales.remove, "steam")


async def _steam_someone_elses_pages(world: World) -> None:
    cog = world.cog(SteamSales)
    await SteamSales.show_page.invoke(cog, world.button("steam-show:999:90:1"), ["999", "90", "1"])


async def _urban_random_turned_off(world: World) -> None:
    world.monkeypatch.setattr(UrbanSettings, "allow_random", False)
    await _run(world, Urban, Urban.random, "urban")


async def _autoreassign_without_manage_roles(world: World) -> None:
    interaction = world.command("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_CHANNELS)
    await AutoReassign.enable.invoke(world.cog(AutoReassign), interaction, [])


REFUSALS: dict[str, Scenario] = {
    "fuel add with nothing spent": _fuel_nothing_spent,
    "fuel add on a day to come": _fuel_date_to_come,
    "fuel efficiency before any refuel": _fuel_no_refuels,
    "invite guild without a support guild": _invite_no_support_guild,
    "reminder add without a time": _reminder_no_time,
    "reminder remove of an unknown one": _reminder_unknown,
    "steam add when subscribed": _steam_already_subscribed,
    "steam remove when not subscribed": _steam_not_subscribed,
    "steam pages of someone else": _steam_someone_elses_pages,
    "urban random when turned off": _urban_random_turned_off,
    "autoreassign enable without Manage Roles": _autoreassign_without_manage_roles,
}


@pytest.fixture
def world(
    engine: Engine,
    make_interaction: InteractionFactory,
    make_component_interaction: ComponentInteractionFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> World:
    return World(engine, make_interaction, make_component_interaction, monkeypatch)


@pytest.mark.parametrize("scenario", REFUSALS.values(), ids=REFUSALS.keys())
async def test_a_refusal_is_a_private_plain_reason(world: World, discord_client: RecordingClient, scenario: Scenario) -> None:
    await scenario(world)

    (response,) = discord_client.interaction_responses()
    data = response["data"]
    assert set(data) == {"content", "flags"}
    assert data["flags"] == EPHEMERAL
    assert data["content"]


# --- Confirmations ---------------------------------------------------------------------------------------------------


CREATED, CHANGED, DELETED = "created", "changed", "deleted"


def _color(kind: str) -> int:
    return int({CREATED: Settings.created_color, CHANGED: Settings.changed_color, DELETED: Settings.deleted_color}[kind])


async def _fuel_add(world: World) -> None:
    await _run(world, Fuel, Fuel.add, "fuel", price=70.0, distance=600.0, amount=40.0)


async def _steam_add(world: World) -> None:
    await _run(world, SteamSales, SteamSales.add, "steam")


async def _steam_percentage(world: World) -> None:
    await _run(world, SteamSales, SteamSales.percentage, "steam", percent=75)


async def _steam_remove(world: World) -> None:
    seed(world.engine, SteamUsers(id=ASKER_ID, sale_threshold=100, last_notification=utc_now()))
    await _run(world, SteamSales, SteamSales.remove, "steam")


async def _autoreassign(world: World, command: Any) -> None:
    interaction = world.command("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
    await command.invoke(world.cog(AutoReassign), interaction, [])


async def _autoreassign_enable(world: World) -> None:
    await _autoreassign(world, AutoReassign.enable)


async def _autoreassign_disable(world: World) -> None:
    seed(world.engine, AutoReassignGuild(id=GUILD_ID))
    await _autoreassign(world, AutoReassign.disable)


CONFIRMATIONS: dict[str, tuple[Scenario, str]] = {
    "fuel add": (_fuel_add, CREATED),
    "steam add": (_steam_add, CREATED),
    "steam percentage": (_steam_percentage, CHANGED),
    "steam remove": (_steam_remove, DELETED),
    "autoreassign enable": (_autoreassign_enable, CREATED),
    "autoreassign disable": (_autoreassign_disable, DELETED),
}


@pytest.mark.parametrize(("scenario", "kind"), CONFIRMATIONS.values(), ids=CONFIRMATIONS.keys())
async def test_a_success_answers_with_its_confirmation_embed(
    world: World,
    discord_client: RecordingClient,
    scenario: Scenario,
    kind: str,
) -> None:
    await scenario(world)

    (response,) = discord_client.interaction_responses()
    data = response["data"]
    assert data["flags"] == EPHEMERAL
    assert "content" not in data
    (embed,) = data["embeds"]
    assert embed["color"] == _color(kind)
    assert embed["description"]


# --- Permissions -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("command", [AutoReassign.enable, AutoReassign.disable], ids=["enable", "disable"])
async def test_autoreassign_names_the_missing_permission(
    world: World,
    discord_client: RecordingClient,
    command: Any,
) -> None:
    seed(world.engine, AutoReassignGuild(id=GUILD_ID))
    interaction = world.command("autoreassign", guild_id=GUILD_ID, permissions=Permissions.SEND_MESSAGES)

    await command.invoke(world.cog(AutoReassign), interaction, [])

    (response,) = discord_client.interaction_responses()
    assert response["data"] == {"content": "You need the Manage Roles permission for that.", "flags": EPHEMERAL}


def test_autoreassign_is_hidden_from_members_without_manage_roles() -> None:
    (group,) = AutoReassign.app_commands()
    assert group.params().default_member_permissions == Permissions.MANAGE_ROLES


# --- Option limits ---------------------------------------------------------------------------------------------------


def _synced_option(cog: type[GroupCog], command: str, option: str) -> dict[str, Any]:
    """Return ``option`` of ``/<group> command`` as the cog's group is synced to Discord."""
    (group,) = cog.app_commands()
    (subcommand,) = (sub for sub in group.params().to_json()["options"] if sub["name"] == command)
    (found,) = (opt for opt in subcommand["options"] if opt["name"] == option)
    return found


OPTION_LIMITS: dict[str, tuple[type[GroupCog], str, str, dict[str, int]]] = {
    "autochannel setup category name": (AutoChannels, "setup", "category_name", {"min_length": 1, "max_length": 100}),
    "autochannel setup hub name": (AutoChannels, "setup", "hub_name", {"min_length": 1, "max_length": 100}),
    "autochannel guild-limit": (AutoChannels, "guild-limit", "limit", {"min_value": 0}),
    "autochannel limit": (AutoChannels, "limit", "limit", {"min_value": 0, "max_value": 99}),
    "autochannel name": (AutoChannels, "name", "name", {"min_length": 1, "max_length": 100}),
    "reminder add": (Reminders, "add", "reminder", {"max_length": 1000}),
    "reminder repeat": (Reminders, "repeat", "reminder", {"max_length": 1000}),
    "steam percentage": (SteamSales, "percentage", "percent", {"min_value": 0, "max_value": 100}),
    "tournament create name": (Tournaments, "create", "name", {"min_length": 1, "max_length": 100}),
    "tournament create team size": (Tournaments, "create", "team_size", {"min_value": 1, "max_value": 25}),
    "tournament team-create": (Tournaments, "team-create", "name", {"min_length": 1, "max_length": 100}),
    "tournament vote question": (Tournaments, "vote", "question", {"max_length": 200}),
}


@pytest.mark.parametrize(("cog", "command", "option", "limits"), OPTION_LIMITS.values(), ids=OPTION_LIMITS.keys())
def test_discord_enforces_the_option_limits(cog: type[GroupCog], command: str, option: str, limits: dict[str, int]) -> None:
    synced = _synced_option(cog, command, option)
    assert {key: synced[key] for key in synced.keys() & {"min_length", "max_length", "min_value", "max_value"}} == limits
