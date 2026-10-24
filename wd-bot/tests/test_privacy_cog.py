"""Unit tests: the privacy cog purges soft-deleted records 30 days after their deletion, and nothing else (sqlite)."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from sqlmodel import Session, select
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import alive, create_or_restore, owned_by, soft_delete
from wd_db.testing import seed, sqlite_engine
from wd_discord import AutocompleteInteraction, GatewayGuild, GuildDelete, Permissions
from wd_discord.gateway import EventName, parse_dispatch, parse_ready
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.interactions import ApplicationCommandOptionType
from wd_discord.resources.user import User
from wd_discord.testing import GUILD_JSON, RecordingClient

from winter_dragon.cogs import privacy
from winter_dragon.cogs.auto_reassign import AutoReassign, AutoReassignGuild, RememberedRole, is_enabled, remembered_roles
from winter_dragon.cogs.autochannel import AutoChannel, AutoChannelHub, AutoChannelSettings, hub_of, owned_channel, settings_of
from winter_dragon.cogs.fuel import CarFuels
from winter_dragon.cogs.privacy import DeletionStep, Privacy, UsageCount
from winter_dragon.cogs.reminder import Reminder, Reminders, owned_reminders
from winter_dragon.cogs.stats import PeakOnline, StatChannel, StatKind, guild_stat_channels
from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties, SteamUsers
from winter_dragon.cogs.steam.store import SteamSaleStore
from winter_dragon.cogs.tournament import service as tournaments
from winter_dragon.cogs.tournament.models import (
    MatchPhase,
    TeamMode,
    Tournament,
    TournamentMatch,
    TournamentPlayer,
    TournamentStatus,
    TournamentTeam,
)


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine
    from wd_bot.auto_reload import AutoReloadWatcher


DAY_0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CREATED = DAY_0 - timedelta(days=5)


def _day(day: int) -> datetime:
    return DAY_0 + timedelta(days=day)


def _reminder(reminder_id: int, *, deleted_at: datetime | None = DAY_0, created_at: datetime = CREATED) -> Reminder:
    return Reminder(
        id=reminder_id,
        content="feed the cat",
        user_id=3,
        timestamp=DAY_0,
        created_at=created_at,
        deleted_at=deleted_at,
    )


def _cog(engine: Engine) -> Privacy:
    return detached_cog(Privacy, engine=engine)


def _created_at_after_storing_again(engine: Engine, reminder_id: int) -> datetime:
    """Store reminder ``reminder_id`` again with create_or_restore; return when the stored row was created."""
    with Session(engine) as session:
        stored = create_or_restore(session, _reminder(reminder_id, deleted_at=None, created_at=DAY_0))
        session.commit()
        return stored.created_at


async def test_a_reminder_deleted_29_days_ago_can_still_be_restored(engine: Engine) -> None:
    seed(engine, _reminder(1))

    await _cog(engine).purge(_day(29))

    assert _created_at_after_storing_again(engine, 1) == CREATED  # restored, not new


async def test_a_reminder_deleted_31_days_ago_is_gone_for_good(engine: Engine) -> None:
    seed(engine, _reminder(1))

    await _cog(engine).purge(_day(31))

    assert _created_at_after_storing_again(engine, 1) == DAY_0  # a fresh one


async def test_alive_reminders_are_never_purged(engine: Engine) -> None:
    seed(engine, _reminder(1, deleted_at=None))

    await _cog(engine).purge(_day(10_000))

    with Session(engine) as session:
        assert [reminder.id for reminder in session.exec(alive(Reminder))] == [1]


async def test_purging_twice_at_the_same_moment_gives_the_same_result(engine: Engine) -> None:
    seed(engine, _reminder(1), _reminder(2, deleted_at=_day(20)), _reminder(3, deleted_at=None))
    cog = _cog(engine)

    await cog.purge(_day(31))
    await cog.purge(_day(31))

    with Session(engine) as session:
        remaining = {reminder.id: reminder.deleted_at for reminder in session.exec(select(Reminder))}
    assert remaining == {2: _day(20), 3: None}


@pytest.fixture
def foreign_keys_engine() -> Engine:
    """Return an in-memory sqlite engine enforcing foreign keys, as postgres does, with every table created."""
    return sqlite_engine(foreign_keys=True)


async def test_a_row_that_fails_is_logged_and_the_others_are_still_purged(
    foreign_keys_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sale = SteamSale(
        id=10,
        title="Game",
        url="https://store.steampowered.com/app/10/",
        sale_percent=100,
        final_price=0.0,
        update_datetime=DAY_0,
        discovered_at=DAY_0,
        deleted_at=DAY_0,
    )
    still_pointing = SteamSaleProperties(steam_sale_id=10, property=SaleTypes.DLC)  # alive: the sale can't go
    seed(foreign_keys_engine, sale, still_pointing, _reminder(1))

    cog = _cog(foreign_keys_engine)
    cog.logger.addHandler(caplog.handler)

    try:
        with caplog.at_level(logging.WARNING):
            await cog.purge(_day(31))
    finally:
        cog.logger.removeHandler(caplog.handler)

    assert "Could not purge SteamSale 10" in caplog.text
    assert _created_at_after_storing_again(foreign_keys_engine, 1) == DAY_0  # the reminder went anyway


async def test_load_starts_the_daily_task_and_unload_cancels_it(engine: Engine) -> None:
    cog = detached_cog(Privacy, engine=engine, loop=asyncio.get_running_loop())
    cog._auto_reloader = cast("AutoReloadWatcher", SimpleNamespace(deregister=lambda: None))  # noqa: SLF001 - what __init__ sets up

    await cog.load()
    task = cog._task  # noqa: SLF001 - the task the cog owns
    assert task is not None
    await asyncio.sleep(0)
    assert not task.done()

    await cog.unload()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cog._task is None  # noqa: SLF001


# --- Departed guilds -------------------------------------------------------------------------------------------------

GUILD_ID = 7
OTHER_GUILD_ID = 8
MEMBER_ID = 3
RIVAL_ID = 4
BOT_USER = {"id": "42", "username": "bot", "discriminator": "0", "bot": True}


class Clock:
    """What the privacy cog's listeners take for now; a test moves it."""

    now: datetime = DAY_0


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    monkeypatch.setattr(privacy, "utc_now", lambda: clock.now)
    return clock


def _guild_delete(client: RecordingClient, guild_id: int = GUILD_ID, *, unavailable: bool = False) -> GuildDelete:
    data: dict[str, object] = {"id": str(guild_id), **({"unavailable": True} if unavailable else {})}
    event = client.receive(parse_dispatch(EventName.GUILD_DELETE, data)).event
    assert isinstance(event, GuildDelete)
    return event


def _guild_create(client: RecordingClient, guild_id: int = GUILD_ID) -> GatewayGuild:
    client.receive(parse_ready({"v": 10, "session_id": "s", "resume_gateway_url": "wss://x", "user": BOT_USER, "guilds": []}))
    data = {
        **GUILD_JSON,
        "id": str(guild_id),
        "large": False,
        "channels": [],
        "threads": [],
        "members": [],
        "voice_states": [],
        "presences": [],
    }
    event = client.receive(parse_dispatch(EventName.GUILD_CREATE, data)).event
    assert isinstance(event, GatewayGuild)
    return event


def _seed_guild(engine: Engine, guild_id: int = GUILD_ID) -> int:
    """Store a hub, roles back on rejoin with a remembered role, stats channels and a running tournament with a vote.

    Return the vote's ID.
    """
    with Session(engine) as session:
        session.add_all(
            [
                AutoChannelHub(id=guild_id, channel_id=guild_id * 100),
                AutoChannel(id=guild_id * 100 + 1, guild_id=guild_id, owner_id=MEMBER_ID),
                AutoReassignGuild(id=guild_id),
                RememberedRole(guild_id=guild_id, user_id=MEMBER_ID, role_id=50),
                StatChannel(id=guild_id * 100 + 2, guild_id=guild_id, kind=StatKind.CATEGORY),
                PeakOnline(id=guild_id, peak=5),
            ],
        )
        tournament = Tournament(
            guild_id=guild_id,
            channel_id=1,
            organiser_id=MEMBER_ID,
            name="cup",
            mode=TeamMode.SOLO,
            team_size=1,
        )
        session.add(tournament)
        session.flush()
        assert tournament.id is not None
        teams = [
            TournamentTeam(tournament_id=tournament.id, name=name, captain_id=user)
            for name, user in (("a", MEMBER_ID), ("b", RIVAL_ID))
        ]
        session.add_all(teams)
        session.flush()
        for team in teams:
            session.add(TournamentPlayer(tournament_id=tournament.id, user_id=team.captain_id, team_id=team.id))
        tournament.status = TournamentStatus.RUNNING
        match = TournamentMatch(
            tournament_id=tournament.id,
            round=0,
            slot=0,
            team_a_id=teams[0].id,
            team_b_id=teams[1].id,
            phase=MatchPhase.LIVE,
        )
        session.add(match)
        session.flush()
        vote = tournaments.open_vote(session, match, "map?", ["dust", "inferno"])
        tournaments.cast(session, vote, MEMBER_ID, 1)
        session.commit()
        assert vote.id is not None
        return vote.id


def _seed_member(engine: Engine) -> None:
    """Store the member's reminder, refuel, Steam subscription and voice-channel preferences."""
    seed(
        engine,
        Reminder(content="feed the cat", user_id=MEMBER_ID, timestamp=DAY_0 + timedelta(days=400)),
        CarFuels(user_id=MEMBER_ID, amount=40, distance=600, price=70),
        SteamUsers(id=MEMBER_ID, sale_threshold=50, last_notification=DAY_0),
        AutoChannelSettings(id=MEMBER_ID, name="my den"),
    )


def _guild_data(engine: Engine, vote_id: int, guild_id: int = GUILD_ID) -> dict[str, object]:
    """Return what the guild's commands and listeners see of its data."""
    with Session(engine) as session:
        tournament = tournaments.active_tournament(session, guild_id)
        tournament_id = None if tournament is None else tournament.id
        return {
            "hub": hub_of(session, guild_id) is not None,
            "own channel": owned_channel(session, guild_id, MEMBER_ID) is not None,
            "roles back": is_enabled(session, guild_id),
            "remembered": [role.role_id for role in remembered_roles(session, guild_id, MEMBER_ID)],
            "stats": [stat.kind for stat in guild_stat_channels(session, guild_id)],
            "tournament": None if tournament is None else tournament.name,
            "teams": [] if tournament_id is None else [team.name for team in tournaments.teams_of(session, tournament_id)],
            "matches": 0 if tournament_id is None else len(tournaments.matches_of(session, tournament_id)),
            "ballots": tournaments.choices_of(session, vote_id),
        }


ALL_THERE = {
    "hub": True,
    "own channel": True,
    "roles back": True,
    "remembered": [50],
    "stats": [StatKind.CATEGORY],
    "tournament": "cup",
    "teams": ["a", "b"],
    "matches": 1,
    "ballots": [1],
}
NOTHING_THERE = {
    "hub": False,
    "own channel": False,
    "roles back": False,
    "remembered": [],
    "stats": [],
    "tournament": None,
    "teams": [],
    "matches": 0,
    "ballots": [],
}


def _member_data(engine: Engine) -> dict[str, object]:
    """Return what the member's own commands and tasks see of their data."""
    with Session(engine) as session:
        return {
            "reminders": [reminder.content for reminder in owned_reminders(session, MEMBER_ID)],
            "refuels": len(session.exec(owned_by(CarFuels, member=MEMBER_ID)).all()),
            "steam": SteamSaleStore(session).subscriber(MEMBER_ID) is not None,
            "channel name": settings_of(session, MEMBER_ID).name,
        }


MEMBER_ALL_THERE = {"reminders": ["feed the cat"], "refuels": 1, "steam": True, "channel name": "my den"}


@pytest.mark.usefixtures("clock")
async def test_a_departed_guild_s_data_is_hidden_and_its_members_own_data_is_not(engine: Engine) -> None:
    vote_id = _seed_guild(engine)
    other_vote_id = _seed_guild(engine, OTHER_GUILD_ID)
    _seed_member(engine)

    await _cog(engine).on_guild_delete(_guild_delete(RecordingClient()))

    assert _guild_data(engine, vote_id) == NOTHING_THERE
    assert _guild_data(engine, other_vote_id, OTHER_GUILD_ID) == ALL_THERE
    assert _member_data(engine) == MEMBER_ALL_THERE


@pytest.mark.usefixtures("clock")
async def test_a_guild_that_only_went_offline_keeps_its_data(engine: Engine) -> None:
    vote_id = _seed_guild(engine)

    await _cog(engine).on_guild_delete(_guild_delete(RecordingClient(), unavailable=True))

    assert _guild_data(engine, vote_id) == ALL_THERE


async def test_a_guild_back_within_30_days_gets_all_of_it_back(engine: Engine, clock: Clock) -> None:
    vote_id = _seed_guild(engine)
    client = RecordingClient()
    cog = _cog(engine)
    await cog.on_guild_delete(_guild_delete(client))

    clock.now = _day(10)
    await cog.on_guild_create(_guild_create(client))

    assert _guild_data(engine, vote_id) == ALL_THERE


async def test_a_setting_removed_before_the_departure_stays_removed(
    engine: Engine,
    clock: Clock,
    make_interaction: InteractionFactory,
    discord_client: RecordingClient,
) -> None:
    vote_id = _seed_guild(engine)
    disable = make_interaction("autoreassign", guild_id=GUILD_ID, permissions=Permissions.MANAGE_ROLES)
    await AutoReassign.disable.invoke(
        detached_cog(AutoReassign, engine=engine, client=discord_client),
        disable,
        disable.options,
    )
    cog = _cog(engine)

    clock.now = datetime.now(UTC) + timedelta(seconds=1)
    await cog.on_guild_delete(_guild_delete(discord_client))
    clock.now += timedelta(days=10)
    await cog.on_guild_create(_guild_create(discord_client))

    assert _guild_data(engine, vote_id) == {**ALL_THERE, "roles back": False, "remembered": []}


async def test_a_guild_back_after_its_data_was_purged_starts_empty(engine: Engine, clock: Clock) -> None:
    vote_id = _seed_guild(engine)
    client = RecordingClient()
    cog = _cog(engine)
    await cog.on_guild_delete(_guild_delete(client))

    await cog.purge(_day(31))
    clock.now = _day(31)
    await cog.on_guild_create(_guild_create(client))

    assert _guild_data(engine, vote_id) == NOTHING_THERE


@pytest.mark.usefixtures("clock")
async def test_a_guild_that_never_departed_is_left_alone_when_it_comes_online(engine: Engine) -> None:
    vote_id = _seed_guild(engine)
    with Session(engine) as session:
        hub = hub_of(session, GUILD_ID)
        assert hub is not None
        soft_delete(session, hub, at=DAY_0 - timedelta(days=1))
        session.commit()

    await _cog(engine).on_guild_create(_guild_create(RecordingClient()))

    assert _guild_data(engine, vote_id) == {**ALL_THERE, "hub": False}


async def test_a_guild_that_departs_twice_comes_back_from_the_first_departure(engine: Engine, clock: Clock) -> None:
    vote_id = _seed_guild(engine)
    client = RecordingClient()
    cog = _cog(engine)
    await cog.on_guild_delete(_guild_delete(client))
    clock.now = _day(1)
    await cog.on_guild_delete(_guild_delete(client))

    clock.now = _day(2)
    await cog.on_guild_create(_guild_create(client))

    assert _guild_data(engine, vote_id) == ALL_THERE


# --- Member deletion requests ----------------------------------------------------------------------------------------

MEMBER_NOTHING_THERE = {"reminders": [], "refuels": 0, "steam": False, "channel name": None}


def _seed_signup(engine: Engine, guild_id: int, mode: TeamMode) -> int:
    """Store a tournament in sign-up, with the member signed up (as captain of team "a" with the rival in captains mode).

    Return its ID.
    """
    with Session(engine) as session:
        tournament = Tournament(guild_id=guild_id, channel_id=1, organiser_id=RIVAL_ID, name="open", mode=mode, team_size=2)
        session.add(tournament)
        session.commit()
        if mode is TeamMode.CAPTAINS:
            tournaments.create_team(session, tournament, MEMBER_ID, "a")
            tournaments.add_to_team(session, tournament, MEMBER_ID, RIVAL_ID)
        else:
            tournaments.sign_up(session, tournament, MEMBER_ID)
            tournaments.sign_up(session, tournament, RIVAL_ID)
        session.commit()
        assert tournament.id is not None
        return tournament.id


def _signups(engine: Engine, tournament_id: int) -> tuple[list[str], list[int]]:
    """Return the tournament's team names and signed-up players."""
    with Session(engine) as session:
        teams = [team.name for team in tournaments.teams_of(session, tournament_id)]
        return teams, [player.user_id for player in tournaments.players_of(session, tournament_id)]


async def _send_due(engine: Engine, now: datetime) -> int:
    return await detached_cog(Reminders, engine=engine, client=RecordingClient()).send_due(now)


async def test_a_deletion_request_hides_all_of_the_member_s_data(engine: Engine) -> None:
    vote_id = _seed_guild(engine)
    _seed_member(engine)
    seed(engine, Reminder(content="due", user_id=MEMBER_ID, timestamp=DAY_0 - timedelta(hours=1)))

    await _cog(engine).request_deletion(MEMBER_ID, DAY_0)

    assert _member_data(engine) == MEMBER_NOTHING_THERE
    assert await _send_due(engine, DAY_0) == 0
    guild = _guild_data(engine, vote_id)
    assert (guild["own channel"], guild["remembered"], guild["ballots"]) == (False, [], [])
    assert (guild["hub"], guild["teams"]) == (True, ["a", "b"])  # the guild's own data stays


async def test_a_deletion_request_takes_the_member_out_of_tournaments_that_have_not_started(engine: Engine) -> None:
    captained = _seed_signup(engine, GUILD_ID, TeamMode.CAPTAINS)
    solo = _seed_signup(engine, OTHER_GUILD_ID, TeamMode.SOLO)

    await _cog(engine).request_deletion(MEMBER_ID, DAY_0)

    assert _signups(engine, captained) == ([], [])  # their team is disbanded
    assert _signups(engine, solo) == ([], [RIVAL_ID])


async def test_a_second_request_while_one_is_pending_changes_nothing(engine: Engine) -> None:
    cog = _cog(engine)
    await cog.request_deletion(MEMBER_ID, DAY_0)
    seed(engine, Reminder(content="after", user_id=MEMBER_ID, timestamp=_day(2)))

    await cog.request_deletion(MEMBER_ID, _day(1))

    assert [step for step, _ in cog.deletion_steps(MEMBER_ID)] == [DeletionStep.REQUESTED, DeletionStep.HIDDEN]
    assert {at for _, at in cog.deletion_steps(MEMBER_ID)} == {DAY_0}
    assert _member_data(engine)["reminders"] == ["after"]


async def test_the_steps_of_a_request_are_recorded_and_its_rows_purged_after_30_days(engine: Engine) -> None:
    seed(engine, _reminder(1, deleted_at=None))
    cog = _cog(engine)

    await cog.request_deletion(MEMBER_ID, DAY_0)
    assert list(cog.deletion_steps(MEMBER_ID)) == [(DeletionStep.REQUESTED, DAY_0), (DeletionStep.HIDDEN, DAY_0)]

    await cog.purge(_day(29))
    assert _created_at_after_storing_again(engine, 1) == CREATED  # still restorable by a guild, say
    with Session(engine) as session:
        soft_delete(session, session.get_one(Reminder, 1), at=DAY_0)
        session.commit()

    await cog.purge(_day(31))
    assert list(cog.deletion_steps(MEMBER_ID)) == [
        (DeletionStep.REQUESTED, DAY_0),
        (DeletionStep.HIDDEN, DAY_0),
        (DeletionStep.PURGED, _day(31)),
    ]
    assert _created_at_after_storing_again(engine, 1) == DAY_0  # gone for good


async def test_a_member_can_request_again_once_the_last_request_is_purged(engine: Engine) -> None:
    cog = _cog(engine)
    await cog.request_deletion(MEMBER_ID, DAY_0)
    await cog.purge(_day(31))
    seed(engine, Reminder(content="new", user_id=MEMBER_ID, timestamp=_day(40)))

    await cog.request_deletion(MEMBER_ID, _day(32))

    assert list(cog.deletion_steps(MEMBER_ID)) == [(DeletionStep.REQUESTED, _day(32)), (DeletionStep.HIDDEN, _day(32))]
    assert _member_data(engine)["reminders"] == []


async def test_a_member_who_asked_for_deletion_while_their_guild_was_away_stays_deleted(engine: Engine, clock: Clock) -> None:
    vote_id = _seed_guild(engine)
    client = RecordingClient()
    cog = _cog(engine)
    await cog.on_guild_delete(_guild_delete(client))

    await cog.request_deletion(MEMBER_ID, _day(1))
    clock.now = _day(5)
    await cog.on_guild_create(_guild_create(client))

    assert _guild_data(engine, vote_id) == {**ALL_THERE, "own channel": False, "remembered": [], "ballots": []}


async def test_a_reminder_added_after_the_request_works_normally(engine: Engine) -> None:
    await _cog(engine).request_deletion(MEMBER_ID, DAY_0)

    seed(engine, Reminder(content="later", user_id=MEMBER_ID, timestamp=_day(1)))

    assert _member_data(engine)["reminders"] == ["later"]
    assert await _send_due(engine, _day(1)) == 1


# --- Command usage counts --------------------------------------------------------------------------------------------


def _subcommand(*path: str) -> list[InteractionDataOption]:
    """Return the options naming the subcommand ``path`` under a command: a group, then its subcommand, or just one."""
    *groups, sub = path
    options = [InteractionDataOption(name=sub, type=ApplicationCommandOptionType.SUB_COMMAND, options=[])]
    for group in reversed(groups):
        options = [InteractionDataOption(name=group, type=ApplicationCommandOptionType.SUB_COMMAND_GROUP, options=options)]
    return options


async def _run(cog: Privacy, make_interaction: InteractionFactory, *path: str, guild_id: int | None = GUILD_ID) -> None:
    command, *sub = path
    await cog.on_interaction(make_interaction(command, options=_subcommand(*sub) if sub else (), guild_id=guild_id))


@pytest.mark.usefixtures("clock")
async def test_each_command_is_counted_per_member_guild_and_day(
    engine: Engine,
    clock: Clock,
    make_interaction: InteractionFactory,
) -> None:
    cog = _cog(engine)

    await _run(cog, make_interaction, "reminder", "add")
    await _run(cog, make_interaction, "reminder", "add")
    await _run(cog, make_interaction, "fuel", "add")
    clock.now = _day(1)
    await _run(cog, make_interaction, "reminder", "add")

    assert set(cog.usage(MEMBER_ID)) == {
        UsageCount(command="reminder add", guild_id=GUILD_ID, day=DAY_0.date(), count=2),
        UsageCount(command="fuel add", guild_id=GUILD_ID, day=DAY_0.date(), count=1),
        UsageCount(command="reminder add", guild_id=GUILD_ID, day=_day(1).date(), count=1),
    }
    assert list(cog.usage(RIVAL_ID)) == []


@pytest.mark.usefixtures("clock")
async def test_a_command_s_full_name_includes_its_group(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog = _cog(engine)

    await _run(cog, make_interaction, "bot", "admin", "sync")
    await _run(cog, make_interaction, "ping")

    assert {count.command for count in cog.usage(MEMBER_ID)} == {"bot admin sync", "ping"}


@pytest.mark.usefixtures("clock")
async def test_a_command_used_in_a_dm_is_counted_without_a_guild(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog = _cog(engine)

    await _run(cog, make_interaction, "reminder", "add", guild_id=None)

    assert list(cog.usage(MEMBER_ID)) == [UsageCount(command="reminder add", guild_id=None, day=DAY_0.date(), count=1)]


@pytest.mark.usefixtures("clock")
async def test_autocomplete_and_button_clicks_are_not_counted(
    engine: Engine,
    make_component_interaction: ComponentInteractionFactory,
    discord_client: RecordingClient,
) -> None:
    cog = _cog(engine)
    autocomplete = AutocompleteInteractionModel(
        id="1",
        application_id="2",
        type=InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE,
        token="tok",  # noqa: S106
        version=1,
        user=User.model_validate({"id": str(MEMBER_ID), "username": "asker", "discriminator": "0"}),
        data=InteractionData(id="10", name="reminder", type=1, options=_subcommand("remove")),
    )

    await cog.on_interaction(AutocompleteInteraction(discord_client, autocomplete))
    await cog.on_interaction(make_component_interaction("tourney-join:1", guild_id=GUILD_ID))

    assert list(cog.usage(MEMBER_ID)) == []


async def test_purge_drops_counts_older_than_12_months(
    engine: Engine,
    clock: Clock,
    make_interaction: InteractionFactory,
) -> None:
    cog = _cog(engine)
    clock.now = DAY_0 - timedelta(days=366)
    await _run(cog, make_interaction, "reminder", "add")
    clock.now = DAY_0 - timedelta(days=300)
    await _run(cog, make_interaction, "fuel", "add")

    await cog.purge(DAY_0)

    assert [count.command for count in cog.usage(MEMBER_ID)] == ["fuel add"]


@pytest.mark.usefixtures("clock")
async def test_a_count_that_can_t_be_stored_is_logged_and_nothing_raises(
    make_interaction: InteractionFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cog = _cog(sqlite_engine(tables=False))  # no tables
    cog.logger.addHandler(caplog.handler)

    try:
        with caplog.at_level(logging.WARNING):
            await _run(cog, make_interaction, "reminder", "add")
    finally:
        cog.logger.removeHandler(caplog.handler)

    assert "Could not count /reminder add" in caplog.text


@pytest.mark.usefixtures("clock")
async def test_a_deletion_request_covers_the_member_s_usage_counts(
    engine: Engine,
    make_interaction: InteractionFactory,
) -> None:
    cog = _cog(engine)
    await _run(cog, make_interaction, "reminder", "add")

    await cog.request_deletion(MEMBER_ID, DAY_0)

    assert list(cog.usage(MEMBER_ID)) == []
