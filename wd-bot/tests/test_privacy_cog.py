"""Unit tests: the privacy cog purges soft-deleted records 30 days after their deletion, and nothing else (sqlite)."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, ClassVar

import pytest
from sqlalchemy import BigInteger
from sqlmodel import Field, Session, select
from wd_bot.testing import detached_cog
from wd_db.extension.lifecycle import (
    DELETED_MEMBER,
    LifecycleModel,
    Ownership,
    alive,
    create_or_restore,
    owned_by,
    soft_delete,
)
from wd_db.testing import seed, sqlite_engine
from wd_discord import AutocompleteInteraction, GatewayGuild, GuildDelete, Permissions
from wd_discord.gateway import EventName, parse_dispatch, parse_ready
from wd_discord.gateway.events import AutocompleteInteraction as AutocompleteInteractionModel
from wd_discord.gateway.events import InteractionData, InteractionDataOption, InteractionType
from wd_discord.interactions import ApplicationCommandOptionType
from wd_discord.resources.user import User
from wd_discord.snowflake import Snowflake
from wd_discord.testing import GUILD_JSON, RecordingClient, user_json

from winter_dragon.cogs.auto_reassign import AutoReassign, AutoReassignGuild, RememberedRole, is_enabled, remembered_roles
from winter_dragon.cogs.autochannel import AutoChannel, AutoChannelHub, AutoChannelSettings, hub_of, owned_channel, settings_of
from winter_dragon.cogs.fuel import CarFuels
from winter_dragon.cogs.privacy import cog as privacy
from winter_dragon.cogs.privacy.cog import Privacy
from winter_dragon.cogs.privacy.domain import (
    DeletionStep,
    HiddenEntry,
    UsageCount,
    category_rows,
    hide_member_data,
    hide_member_rows,
    restorable_rows,
    restore_member_rows,
    stored_models,
)
from winter_dragon.cogs.reminder.cog import Reminders
from winter_dragon.cogs.reminder.domain import Reminder, owned_reminders
from winter_dragon.cogs.stats import PeakOnline, StatChannel, StatKind, guild_stat_channels
from winter_dragon.cogs.steam.models import SaleTypes, SteamSale, SteamSaleProperties, SteamUsers
from winter_dragon.cogs.steam.store import SteamSaleStore
from winter_dragon.cogs.team import service as team_service
from winter_dragon.cogs.team.models import Team, TeamKind, TeamMember, TeamOrigin
from winter_dragon.cogs.tournament import service as tournaments
from winter_dragon.cogs.tournament.models import (
    EntryPlayer,
    MatchLineup,
    MatchPhase,
    MatchVote,
    TeamMode,
    Tournament,
    TournamentEntry,
    TournamentMatch,
    TournamentSignup,
    TournamentStatus,
)
from winter_dragon.data_categories import DataCategory
from winter_dragon.member_hidden import MemberHiddenHook
from winter_dragon.web.records import member_records


if TYPE_CHECKING:
    from conftest import ComponentInteractionFactory, InteractionFactory
    from sqlalchemy import Engine


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


# --- Departed guilds -------------------------------------------------------------------------------------------------

GUILD_ID = 7
OTHER_GUILD_ID = 8
MEMBER_ID = 3
RIVAL_ID = 4
BOT_USER = user_json(id="42", username="bot", bot=True)


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
            organiser_id=MEMBER_ID,
            name="cup",
            mode=TeamMode.SOLO,
            team_size=1,
        )
        session.add(tournament)
        session.flush()
        assert tournament.id is not None
        teams: list[TournamentEntry] = []
        for name, captain in (("a", MEMBER_ID), ("b", RIVAL_ID)):
            team = team_service.create_team(session, name, captain)
            entry = TournamentEntry(tournament_id=tournament.id, team_id=team.id or 0, name=name)
            session.add(entry)
            session.flush()
            session.add(EntryPlayer(entry_id=entry.id or 0, user_id=captain))
            teams.append(entry)
        tournament.status = TournamentStatus.RUNNING
        match = TournamentMatch(
            tournament_id=tournament.id,
            round=0,
            slot=0,
            entry_a_id=teams[0].id,
            entry_b_id=teams[1].id,
            phase=MatchPhase.LIVE,
        )
        session.add(match)
        session.flush()
        vote = tournaments.open_vote(session, match, "map?", ["dust", "inferno"], MEMBER_ID)
        session.add(MatchLineup(match_id=match.id or 0, entry_id=teams[0].id or 0, user_id=MEMBER_ID))
        session.flush()
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
        tournament = next(iter(tournaments.visible_tournaments(session, guild_id, MEMBER_ID, None)), None)
        vote = session.get(MatchVote, vote_id)
        return {
            "hub": hub_of(session, guild_id) is not None,
            "own channel": owned_channel(session, guild_id, MEMBER_ID) is not None,
            "roles back": is_enabled(session, guild_id),
            "remembered": [role.role_id for role in remembered_roles(session, guild_id, MEMBER_ID)],
            "stats": [stat.kind for stat in guild_stat_channels(session, guild_id)],
            "tournament": None if tournament is None else tournament.name,
            "teams": [] if tournament is None else [team.name for team in tournaments.entries_of(session, tournament)],
            "matches": 0 if tournament is None else len(tournaments.matches_of(session, tournament)),
            "ballots": [] if vote is None else tournaments.choices_of(session, vote),
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
        tournament = Tournament(guild_id=guild_id, organiser_id=RIVAL_ID, name="open", mode=mode, team_size=2)
        session.add(tournament)
        session.commit()
        if mode is TeamMode.CAPTAINS:
            team = team_service.create_team(session, "a", MEMBER_ID)
            session.commit()
            entry = tournaments.enter(session, tournament, team, MEMBER_ID)
            team_service.join(session, team, RIVAL_ID)
            tournaments.add_player(session, tournament, entry, MEMBER_ID, RIVAL_ID)
        else:
            tournaments.sign_up(session, tournament, MEMBER_ID)
            tournaments.sign_up(session, tournament, RIVAL_ID)
        session.commit()
        assert tournament.id is not None
        return tournament.id


def _signups(engine: Engine, tournament_id: int) -> tuple[list[str], list[int]]:
    """Return the tournament's team names and signed-up players."""
    with Session(engine) as session:
        tournament = session.get_one(Tournament, tournament_id)
        teams = [team.name for team in tournaments.entries_of(session, tournament)]
        return teams, [signup.user_id for signup in tournaments.signups_of(session, tournament)]


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

    assert _signups(engine, captained) == (["a"], [])  # the team hands over to the rival, and its entry stays with it
    assert _signups(engine, solo) == ([], [RIVAL_ID])


HIDDEN_BY_TEST_HOOK: list[int] = []
"""The members :class:`FeatureHook` saw hidden."""


class FeatureHook(MemberHiddenHook):
    """A feature outside the privacy cog that cleans up after a hidden member; defining it registers it."""

    @classmethod
    def on_member_hidden(cls, session: Session, member_id: Snowflake) -> None:
        HIDDEN_BY_TEST_HOOK.append(member_id)


async def test_a_deletion_request_runs_every_registered_member_hidden_hook(engine: Engine) -> None:
    HIDDEN_BY_TEST_HOOK.clear()

    await _cog(engine).request_deletion(MEMBER_ID, DAY_0)

    assert HIDDEN_BY_TEST_HOOK == [MEMBER_ID]


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
        UsageCount(command="reminder add", guild_id=Snowflake(GUILD_ID), day=DAY_0.date(), count=2),
        UsageCount(command="fuel add", guild_id=Snowflake(GUILD_ID), day=DAY_0.date(), count=1),
        UsageCount(command="reminder add", guild_id=Snowflake(GUILD_ID), day=_day(1).date(), count=1),
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
async def test_a_command_used_twice_in_a_dm_is_counted_twice(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog = _cog(engine)

    await _run(cog, make_interaction, "ping", guild_id=None)
    await _run(cog, make_interaction, "ping", guild_id=None)

    assert list(cog.usage(MEMBER_ID)) == [UsageCount(command="ping", guild_id=None, day=DAY_0.date(), count=2)]


@pytest.mark.usefixtures("clock")
async def test_a_hidden_count_starts_again_from_one(engine: Engine, make_interaction: InteractionFactory) -> None:
    cog = _cog(engine)
    await _run(cog, make_interaction, "ping")
    await _run(cog, make_interaction, "ping")
    hide_member_data(engine, MEMBER_ID, DAY_0)

    await _run(cog, make_interaction, "ping")

    assert list(cog.usage(MEMBER_ID)) == [UsageCount(command="ping", guild_id=Snowflake(GUILD_ID), day=DAY_0.date(), count=1)]


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
        user=User.model_validate(user_json(id=str(MEMBER_ID), username="asker")),
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


class AnonymisedScore(LifecycleModel, table=True):
    """A test table whose ``player_id`` a deletion request anonymises."""

    anonymised: ClassVar[tuple[str, ...]] = ("player_id",)

    player_id: int = Field(sa_type=BigInteger)


@pytest.mark.usefixtures("clock")
async def test_a_deletion_request_anonymises_rows_instead_of_hiding_them(engine: Engine) -> None:
    member_row, other_row = seed(engine, AnonymisedScore(player_id=MEMBER_ID), AnonymisedScore(player_id=999))

    await _cog(engine).request_deletion(MEMBER_ID, DAY_0)

    with Session(engine) as session:
        alive_ids = {row.id for row in session.exec(alive(AnonymisedScore)).all()}
        assert alive_ids == {member_row, other_row}
        assert session.get(AnonymisedScore, member_row).player_id == DELETED_MEMBER
        assert session.get(AnonymisedScore, other_row).player_id == 999


async def test_the_data_page_lists_rows_a_deletion_request_anonymises(engine: Engine) -> None:
    seed(engine, AnonymisedScore(player_id=MEMBER_ID))

    assert AnonymisedScore in [record.model for record in member_records(engine, Snowflake(MEMBER_ID))]


async def test_a_finished_tournament_and_its_winning_entry_are_purged_together() -> None:
    engine = sqlite_engine(foreign_keys=True)
    with Session(engine) as session:
        tournament = Tournament(guild_id=1, organiser_id=2, name="Cup", mode=TeamMode.SOLO, team_size=1)
        team = Team(name="A", kind=TeamKind.TEMPORARY, origin=TeamOrigin.SOLO_TOURNAMENT)
        session.add_all([tournament, team])
        session.flush()
        entry = TournamentEntry(tournament_id=tournament.id or 0, team_id=team.id or 0, name="A")
        session.add(entry)
        session.flush()
        tournament.winner_entry_id = entry.id  # the tournament points at its entry, and the entry at its tournament
        for row in (entry, tournament, team):
            row.deleted_at = DAY_0
        session.commit()

    await _cog(engine).purge(_day(31))

    with Session(engine) as session:
        assert session.exec(select(Tournament)).all() == []
        assert session.exec(select(TournamentEntry)).all() == []
        assert session.exec(select(Team)).all() == []


# --- Deleting part of a member's data ------------------------------------------------------------------------------


def _alive_ids[M: LifecycleModel](engine: Engine, model: type[M]) -> list[int]:
    with Session(engine) as session:
        return sorted(row.id or 0 for row in session.exec(alive(model)))


def test_hiding_chosen_rows_hides_only_those(engine: Engine) -> None:
    seed(
        engine,
        Reminder(id=1, content="keep", user_id=MEMBER_ID, timestamp=DAY_0),
        Reminder(id=2, content="drop", user_id=MEMBER_ID, timestamp=DAY_0),
    )

    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {2}}, DAY_0)

    assert _alive_ids(engine, Reminder) == [1]


def test_a_row_of_another_member_can_not_be_chosen(engine: Engine) -> None:
    seed(engine, Reminder(id=1, content="theirs", user_id=RIVAL_ID, timestamp=DAY_0))

    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0)

    assert _alive_ids(engine, Reminder) == [1]


def test_a_chosen_row_in_someone_else_s_history_is_anonymised_not_hidden(engine: Engine) -> None:
    _seed_guild(engine)
    with Session(engine) as session:
        lineup = session.exec(alive(MatchLineup)).one()

    hide_member_rows(engine, Snowflake(MEMBER_ID), {MatchLineup: {lineup.id or 0}}, DAY_0)

    with Session(engine) as session:
        assert [row.user_id for row in session.exec(alive(MatchLineup))] == [DELETED_MEMBER]


def test_a_chosen_team_membership_leaves_the_team_and_hands_over_the_captaincy(engine: Engine) -> None:
    with Session(engine) as session:
        team = team_service.create_team(session, "a", MEMBER_ID)
        team_service.join(session, team, RIVAL_ID)
        session.commit()
        own = team_service.membership(session, team, MEMBER_ID)
        assert own is not None

    hide_member_rows(engine, Snowflake(MEMBER_ID), {TeamMember: {own.id or 0}}, DAY_0)

    with Session(engine) as session:
        stored = session.get_one(Team, team.id)
        assert stored.captain_id == RIVAL_ID
        assert [member.user_id for member in team_service.members_of(session, stored)] == [RIVAL_ID]


def test_a_chosen_place_in_a_tournament_in_sign_up_withdraws_the_member(engine: Engine) -> None:
    solo = _seed_signup(engine, GUILD_ID, TeamMode.SOLO)
    with Session(engine) as session:
        signup = next(row for row in session.exec(alive(TournamentSignup)) if row.user_id == MEMBER_ID)

    hide_member_rows(engine, Snowflake(MEMBER_ID), {TournamentSignup: {signup.id or 0}}, DAY_0)

    assert _signups(engine, solo) == ([], [RIVAL_ID])


def test_a_whole_feature_hides_every_row_of_it_and_nothing_else(engine: Engine) -> None:
    _seed_member(engine)
    seed(engine, Reminder(content="second", user_id=MEMBER_ID, timestamp=DAY_0))

    chosen = category_rows(engine, Snowflake(MEMBER_ID), {DataCategory.of(Reminder)})
    hide_member_rows(engine, Snowflake(MEMBER_ID), chosen, DAY_0)

    data = _member_data(engine)
    assert data["reminders"] == []
    assert (data["refuels"], data["steam"]) == (1, True)  # other features stay


def test_every_table_holding_member_data_is_registered_under_a_feature(engine: Engine) -> None:
    member_tables = [
        model
        for model in stored_models(engine)
        if model.__module__.startswith("winter_dragon.") and (model.ownership.member is not None or model.anonymised)
    ]

    unregistered = [model.__name__ for model in member_tables if DataCategory.registered_for(model) is None]

    assert member_tables
    assert unregistered == []


async def test_chosen_rows_are_purged_30_days_after_they_were_hidden(engine: Engine) -> None:
    seed(engine, Reminder(id=1, content="drop", user_id=MEMBER_ID, timestamp=DAY_0))
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0)

    await _cog(engine).purge(_day(31))

    with Session(engine) as session:
        assert session.exec(select(Reminder)).all() == []


# --- Deleting at once, and restoring -------------------------------------------------------------------------------


def _reminders(engine: Engine, *ids: int) -> None:
    seed(
        engine,
        *(Reminder(id=reminder_id, content=f"r{reminder_id}", user_id=MEMBER_ID, timestamp=DAY_0) for reminder_id in ids),
    )


def _stored_ids(engine: Engine) -> list[int]:
    with Session(engine) as session:
        return sorted(row.id or 0 for row in session.exec(select(Reminder)))


def test_deleting_now_purges_the_chosen_rows_at_once(engine: Engine) -> None:
    _reminders(engine, 1, 2)

    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {2}}, DAY_0, delete_now=True)

    assert _stored_ids(engine) == [1]


def test_deleting_now_still_anonymises_a_row_in_someone_else_s_history(engine: Engine) -> None:
    _seed_guild(engine)
    with Session(engine) as session:
        lineup = session.exec(alive(MatchLineup)).one()

    hide_member_rows(engine, Snowflake(MEMBER_ID), {MatchLineup: {lineup.id or 0}}, DAY_0, delete_now=True)

    with Session(engine) as session:
        assert [row.user_id for row in session.exec(alive(MatchLineup))] == [DELETED_MEMBER]


def test_hidden_rows_can_be_restored_within_30_days(engine: Engine) -> None:
    _reminders(engine, 1, 2)
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {2}}, DAY_0)

    assert restorable_rows(engine, Snowflake(MEMBER_ID), _day(29)) == {Reminder: {2}}
    assert restore_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {2}}, _day(29)) == 1

    assert _alive_ids(engine, Reminder) == [1, 2]
    assert restorable_rows(engine, Snowflake(MEMBER_ID), _day(29)) == {}


def test_a_hidden_row_can_not_be_restored_after_30_days(engine: Engine) -> None:
    _reminders(engine, 1)
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0)

    assert restorable_rows(engine, Snowflake(MEMBER_ID), _day(31)) == {}
    assert restore_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, _day(31)) == 0
    assert _alive_ids(engine, Reminder) == []


def test_rows_deleted_now_can_not_be_restored(engine: Engine) -> None:
    _reminders(engine, 1)
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0, delete_now=True)

    assert restorable_rows(engine, Snowflake(MEMBER_ID), DAY_0) == {}


def test_only_rows_the_member_hid_can_be_restored(engine: Engine) -> None:
    seed(engine, _reminder(1))  # the member's, soft-deleted by the reminder cog once it fired

    assert restorable_rows(engine, Snowflake(MEMBER_ID), DAY_0) == {}
    assert restore_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0) == 0
    assert _alive_ids(engine, Reminder) == []


def test_a_member_can_not_restore_someone_else_s_rows(engine: Engine) -> None:
    _reminders(engine, 1)
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0)

    assert restore_member_rows(engine, Snowflake(RIVAL_ID), {Reminder: {1}}, DAY_0) == 0
    assert _alive_ids(engine, Reminder) == []


def test_a_deletion_request_can_not_be_undone_by_restoring(engine: Engine) -> None:
    _reminders(engine, 1, 2)
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0)

    hide_member_data(engine, Snowflake(MEMBER_ID), _day(1))

    assert restorable_rows(engine, Snowflake(MEMBER_ID), _day(1)) == {}


def test_leaving_a_team_can_not_be_restored(engine: Engine) -> None:
    with Session(engine) as session:
        team = team_service.create_team(session, "a", MEMBER_ID)
        team_service.join(session, team, RIVAL_ID)
        session.commit()
        own = team_service.membership(session, team, MEMBER_ID)
        assert own is not None

    hide_member_rows(engine, Snowflake(MEMBER_ID), {TeamMember: {own.id or 0}}, DAY_0)

    assert restorable_rows(engine, Snowflake(MEMBER_ID), DAY_0) == {}


async def test_the_purge_forgets_what_could_be_restored_once_it_s_purged(engine: Engine) -> None:
    _reminders(engine, 1)
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Reminder: {1}}, DAY_0)

    await _cog(engine).purge(_day(31))

    with Session(engine) as session:
        assert session.exec(select(HiddenEntry)).all() == []


class Notebook(LifecycleModel, table=True):
    """A test table a member owns, which :class:`NotebookPage` rows point at."""

    ownership: ClassVar[Ownership] = Ownership(member="owner_id")

    owner_id: int = Field(sa_type=BigInteger)


class NotebookPage(LifecycleModel, table=True):
    """A test table a member owns, a child of :class:`Notebook` by foreign key."""

    ownership: ClassVar[Ownership] = Ownership(member="owner_id")

    owner_id: int = Field(sa_type=BigInteger)
    notebook_id: int = Field(foreign_key="notebook.id")


def test_restoring_a_row_brings_back_the_parent_the_member_hid_with_it(engine: Engine) -> None:
    seed(engine, Notebook(id=1, owner_id=MEMBER_ID), NotebookPage(id=1, owner_id=MEMBER_ID, notebook_id=1))
    hide_member_rows(engine, Snowflake(MEMBER_ID), {Notebook: {1}, NotebookPage: {1}}, DAY_0)

    assert restore_member_rows(engine, Snowflake(MEMBER_ID), {NotebookPage: {1}}, DAY_0) == 2

    assert (_alive_ids(engine, Notebook), _alive_ids(engine, NotebookPage)) == ([1], [1])
    assert restorable_rows(engine, Snowflake(MEMBER_ID), DAY_0) == {}


def test_a_row_whose_parent_is_hidden_for_another_reason_stays_hidden(engine: Engine) -> None:
    seed(engine, Notebook(id=1, owner_id=MEMBER_ID), NotebookPage(id=1, owner_id=MEMBER_ID, notebook_id=1))
    hide_member_rows(engine, Snowflake(MEMBER_ID), {NotebookPage: {1}}, DAY_0)
    with Session(engine) as session:
        soft_delete(session, session.get_one(Notebook, 1), at=DAY_0)  # by its feature, not by the member
        session.commit()

    assert restore_member_rows(engine, Snowflake(MEMBER_ID), {NotebookPage: {1}}, DAY_0) == 0

    assert _alive_ids(engine, NotebookPage) == []
    assert restorable_rows(engine, Snowflake(MEMBER_ID), DAY_0) == {NotebookPage: {1}}
