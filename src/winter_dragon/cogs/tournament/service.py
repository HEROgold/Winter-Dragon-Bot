"""What can happen to a tournament: signing up, forming teams, running the bracket, drafting and voting.

Each action takes an open session and leaves committing to the caller. An action that isn't allowed raises
:class:`~wd_errors.Refused` saying why, for the player; the caller then drops the session's changes.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session, col, select
lazy from herogold.state import StateMachine
lazy from sqlalchemy import exists
lazy from sqlalchemy.orm import aliased
lazy from wd_db.extension.lifecycle import DELETED_MEMBER, alive, alive_by_id, create_or_restore, soft_delete, upsert
lazy from wd_discord.snowflake import Snowflake
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.team.models import Team, TeamKind, TeamOrigin
lazy from winter_dragon.cogs.team.service import create_temporary_teams, end_team, membership
lazy from winter_dragon.cogs.team.split import split_into_teams
lazy from winter_dragon.member_hidden import MemberHiddenHook, RemovedRows
lazy from winter_dragon.stored import stored

lazy from .bracket import BracketSlot, first_round, next_match, round_count, valid_options
lazy from .models import (
    ACTIVE,
    DraftChoice,
    DraftKind,
    EntryPlayer,
    LineupChange,
    MatchBallot,
    MatchEvent,
    MatchEventKind,
    MatchLineup,
    MatchPhase,
    MatchStep,
    MatchVote,
    TeamMode,
    Tournament,
    TournamentEntry,
    TournamentMatch,
    TournamentPost,
    TournamentSignup,
    TournamentStatus,
)


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence
    lazy from datetime import datetime
    lazy from random import Random

    lazy from sqlmodel.sql.expression import SelectOfScalar
    lazy from wd_db.extension.lifecycle import LifecycleModel


def visible_tournaments(
    session: Session,
    guild_id: Snowflake,
    user_id: Snowflake,
    channel_id: Snowflake | None,
    *,
    include_over: bool = False,
) -> Generator[Tournament]:
    """Yield the guild's tournaments that ``user_id`` organises, signed up for, or that are posted in ``channel_id``, by name.

    Only the tournaments that aren't over, unless ``include_over`` yields every status.
    """
    query = alive(Tournament).where(Tournament.guild_id == int(guild_id)).order_by(col(Tournament.name))
    if not include_over:
        query = query.where(col(Tournament.status).in_(ACTIVE))
    signed_up = _joined_tournament_ids(session, user_id)
    posted = set()
    if channel_id is not None:
        posted = {
            post.tournament_id
            for post in session.exec(alive(TournamentPost).where(TournamentPost.channel_id == int(channel_id)))
        }
    visible = [
        tournament
        for tournament in session.exec(query)
        if tournament.organiser_id == int(user_id) or tournament.id in signed_up or tournament.id in posted
    ]
    yield from visible


def posts_of(session: Session, tournament: Tournament) -> Generator[TournamentPost]:
    """Yield the tournament's posts."""
    yield from session.exec(
        alive(TournamentPost).where(TournamentPost.tournament_id == _id(tournament)).order_by(col(TournamentPost.id)),
    )


def add_post(session: Session, tournament: Tournament, channel_id: Snowflake, message_id: Snowflake) -> None:
    """Record that the tournament is shown by ``message_id`` in ``channel_id``."""
    session.add(TournamentPost(tournament_id=_id(tournament), channel_id=int(channel_id), message_id=int(message_id)))


def _joined_tournament_ids(session: Session, user_id: Snowflake) -> set[int]:
    """Return the IDs of the tournaments ``user_id`` signed up for alone, or plays for in an entry."""
    joined = {
        signup.tournament_id for signup in session.exec(alive(TournamentSignup).where(TournamentSignup.user_id == int(user_id)))
    }
    entry_ids = [player.entry_id for player in session.exec(alive(EntryPlayer).where(EntryPlayer.user_id == int(user_id)))]
    if entry_ids:
        joined |= {
            entry.tournament_id for entry in session.exec(alive(TournamentEntry).where(col(TournamentEntry.id).in_(entry_ids)))
        }
    return joined


def signups_of(session: Session, tournament: Tournament) -> list[TournamentSignup]:
    """Return everyone signed up alone for the tournament, in sign-up order."""
    query = alive(TournamentSignup).where(TournamentSignup.tournament_id == _id(tournament)).order_by(col(TournamentSignup.id))
    return list(session.exec(query))


def signup_of(session: Session, tournament: Tournament, user_id: Snowflake) -> TournamentSignup | None:
    """Return the user's solo sign-up for the tournament, if any."""
    query = alive(TournamentSignup).where(
        TournamentSignup.tournament_id == _id(tournament),
        TournamentSignup.user_id == int(user_id),
    )
    return session.exec(query).first()


def entries_of(session: Session, tournament: Tournament) -> list[TournamentEntry]:
    """Return the tournament's teams, in the order they were formed."""
    query = alive(TournamentEntry).where(TournamentEntry.tournament_id == _id(tournament)).order_by(col(TournamentEntry.id))
    return list(session.exec(query))


def roster(session: Session, entry: TournamentEntry) -> list[Snowflake]:
    """Return the user IDs of the entry's players."""
    return [Snowflake(player.user_id) for player in _players_of_entry(session, entry)]


def _players_of_entry(session: Session, entry: TournamentEntry) -> list[EntryPlayer]:
    """Return the entry's player rows, in the order they were added."""
    return list(session.exec(alive(EntryPlayer).where(EntryPlayer.entry_id == _id(entry)).order_by(col(EntryPlayer.id))))


def _player_of_entry(session: Session, entry: TournamentEntry, user_id: Snowflake) -> EntryPlayer | None:
    """Return the player row of ``user_id`` in the entry, if they play for it."""
    query = alive(EntryPlayer).where(EntryPlayer.entry_id == _id(entry), EntryPlayer.user_id == int(user_id))
    return session.exec(query).first()


def matches_of(session: Session, tournament: Tournament) -> list[TournamentMatch]:
    """Return the tournament's matches, round by round, top to bottom."""
    query = (
        alive(TournamentMatch)
        .where(TournamentMatch.tournament_id == _id(tournament))
        .order_by(col(TournamentMatch.round), col(TournamentMatch.slot))
    )
    return list(session.exec(query))


def _id(record: Tournament | Team | TournamentEntry | TournamentMatch | MatchVote) -> int:
    """Return a stored record's ID."""
    if record.id is None:
        msg = f"{type(record).__name__} isn't stored yet"
        raise ValueError(msg)
    return record.id


def record_event(
    session: Session,
    match: TournamentMatch,
    kind: MatchEventKind,
    actor_id: Snowflake,
    detail: str = "",
) -> None:
    """Record that ``actor_id`` did ``kind`` in ``match`` now, with a short ``detail``."""
    session.add(MatchEvent(match_id=_id(match), kind=kind, actor_id=int(actor_id), at=utc_now(), detail=detail))


def match_log(session: Session, match: TournamentMatch) -> list[MatchEvent | LineupChange]:
    """Return what happened in ``match``: its events, and the lineup changes made for it, oldest first."""
    match_id = _id(match)
    entry_ids = [entry_id for entry_id in (match.entry_a_id, match.entry_b_id) if entry_id is not None]
    events = session.exec(alive(MatchEvent).where(MatchEvent.match_id == match_id))
    changes = session.exec(
        alive(LineupChange).where(LineupChange.match_id == match_id, col(LineupChange.entry_id).in_(entry_ids)),
    )
    logged: list[MatchEvent | LineupChange] = [*events, *changes]
    return sorted(logged, key=_logged_at)


def _logged_at(row: MatchEvent | LineupChange) -> datetime:
    """Return when a logged row happened."""
    return row.at if isinstance(row, MatchEvent) else row.changed_at


# --- Sign-up ---------------------------------------------------------------------------------------------------------


def sign_up(session: Session, tournament: Tournament, user_id: Snowflake) -> None:
    """Sign ``user_id`` up for a solo tournament."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "Sign-up for this tournament is closed."
        raise Refused(msg)
    if tournament.mode is not TeamMode.SOLO:
        msg = "Teams sign up for this tournament; a captain enters a team with /tournament enter."
        raise Refused(msg)
    if signup_of(session, tournament, user_id) is not None:
        msg = "You're signed up already."
        raise Refused(msg)
    create_or_restore(session, TournamentSignup(tournament_id=_id(tournament), user_id=int(user_id)))


def open_signups_of(session: Session, user_id: Snowflake) -> Generator[Tournament]:
    """Yield the tournaments ``user_id`` signed up for, alone or in an entry, that haven't started."""
    tournament_ids = _joined_tournament_ids(session, user_id)
    if not tournament_ids:
        return
    query = alive(Tournament).where(col(Tournament.id).in_(tournament_ids), Tournament.status == TournamentStatus.SIGNUP)
    yield from session.exec(query)


def withdraw(session: Session, tournament: Tournament, user_id: Snowflake) -> None:
    """Take ``user_id`` out of the tournament before it starts; a captain leaving withdraws their entry."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started; ask the organiser to forfeit your matches instead."
        raise Refused(msg)
    if tournament.mode is TeamMode.SOLO:
        signup = signup_of(session, tournament, user_id)
        if signup is None:
            msg = "You aren't signed up."
            raise Refused(msg)
        soft_delete(session, signup)
        return
    players = list(session.exec(_players_in(tournament, user_id)))
    if not players:
        msg = "You aren't signed up."
        raise Refused(msg)
    captained = entry_of_captain(session, tournament, user_id)
    for player in players:
        soft_delete(session, player)
    if captained is not None:
        _withdraw_entry(session, captained)


def _withdraw_entry(session: Session, entry: TournamentEntry) -> None:
    """Soft-delete ``entry`` and every player in it."""
    for player in _players_of_entry(session, entry):
        soft_delete(session, player)
    soft_delete(session, entry)


class WithdrawHiddenMember(MemberHiddenHook):
    """A member whose data is hidden leaves each tournament that hasn't started.

    Unlike ``/tournament leave``, a captain's entry stays: their team hands its captaincy over (the team cog's hook),
    so only the member's own places go. An entry left without players is withdrawn. Either hook may run first.
    """

    tables = (Tournament, TournamentEntry, TournamentSignup, EntryPlayer)

    @classmethod
    @override
    def on_member_hidden(cls, session: Session, member_id: Snowflake) -> None:
        """Take the member ``member_id`` out of every tournament they're in that hasn't started."""
        for tournament in list(open_signups_of(session, member_id)):
            if tournament.mode is TeamMode.SOLO:
                withdraw(session, tournament, member_id)
                continue
            for player in list(session.exec(_players_in(tournament, member_id))):
                soft_delete(session, player)
                session.flush()
                entry = alive_by_id(session, TournamentEntry, player.entry_id)
                if entry is not None and not roster(session, entry):
                    _withdraw_entry(session, entry)

    @classmethod
    @override
    def removes(cls, member_id: Snowflake) -> Generator[RemovedRows]:
        """Yield the entries the member ``member_id`` is the only player of, in tournaments that haven't started."""
        others = aliased(EntryPlayer)
        sole = (
            select(col(TournamentEntry.id))
            .join(Tournament, col(TournamentEntry.tournament_id) == col(Tournament.id))
            .join(EntryPlayer, col(EntryPlayer.entry_id) == col(TournamentEntry.id))
            .where(
                EntryPlayer.user_id == int(member_id),
                col(EntryPlayer.deleted_at).is_(None),
                col(TournamentEntry.deleted_at).is_(None),
                col(Tournament.deleted_at).is_(None),
                Tournament.status == TournamentStatus.SIGNUP,
                ~exists().where(
                    col(others.entry_id) == col(TournamentEntry.id),
                    col(others.user_id) != int(member_id),
                    col(others.deleted_at).is_(None),
                ),
            )
        )
        yield RemovedRows(TournamentEntry, sole)


def _players_in(tournament: Tournament, user_id: Snowflake) -> SelectOfScalar[EntryPlayer]:
    """Select ``user_id``'s alive places in the entries of ``tournament``."""
    return (
        alive(EntryPlayer)
        .join(TournamentEntry, col(EntryPlayer.entry_id) == col(TournamentEntry.id))
        .where(TournamentEntry.tournament_id == _id(tournament), EntryPlayer.user_id == int(user_id))
    )


def enter(session: Session, tournament: Tournament, team: Team, captain_id: Snowflake) -> TournamentEntry:
    """Enter the lasting ``team`` into ``tournament`` for its captain, with the captain as its first player."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started; entries can't change any more."
        raise Refused(msg)
    if tournament.mode is not TeamMode.CAPTAINS:
        msg = "Players sign up alone for this tournament, and are put in teams when it starts."
        raise Refused(msg)
    if team.kind is not TeamKind.LASTING or team.captain_id != int(captain_id):
        msg = "Only the team's captain can enter it."
        raise Refused(msg)
    if any(entry.team_id == _id(team) for entry in entries_of(session, tournament)):
        msg = "That team has entered already."
        raise Refused(msg)
    if any(entry.name.casefold() == team.name.casefold() for entry in entries_of(session, tournament)):
        msg = "An entry has that name already."
        raise Refused(msg)
    entry = TournamentEntry(tournament_id=_id(tournament), team_id=_id(team), name=team.name)
    session.add(entry)
    session.flush()
    create_or_restore(session, EntryPlayer(entry_id=_id(entry), user_id=int(captain_id)))
    return entry


def _captain_of(session: Session, entry: TournamentEntry, captain_id: Snowflake) -> Team:
    """Return the entry's team if ``captain_id`` captains it; refuse otherwise."""
    team = alive_by_id(session, Team, entry.team_id)
    if team is None or team.captain_id != int(captain_id):
        msg = "Only a team's captain can change its entry."
        raise Refused(msg)
    return team


def add_player(
    session: Session,
    tournament: Tournament,
    entry: TournamentEntry,
    captain_id: Snowflake,
    user_id: Snowflake,
) -> None:
    """Add the team member ``user_id`` to ``entry``'s players, for its captain."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started; entries can't change any more."
        raise Refused(msg)
    team = _captain_of(session, entry, captain_id)
    if membership(session, team, user_id) is None:
        msg = "They aren't in your team."
        raise Refused(msg)
    if _player_of_entry(session, entry, user_id) is not None:
        msg = "They're in this entry already."
        raise Refused(msg)
    if len(roster(session, entry)) >= tournament.team_size:
        msg = f"Your entry is full: entries have {tournament.team_size} players."
        raise Refused(msg)
    create_or_restore(session, EntryPlayer(entry_id=_id(entry), user_id=int(user_id)))


def remove_player(
    session: Session,
    tournament: Tournament,
    entry: TournamentEntry,
    captain_id: Snowflake,
    user_id: Snowflake,
) -> None:
    """Take ``user_id`` off ``entry``'s players, for its captain; the captain stays."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started; entries can't change any more."
        raise Refused(msg)
    _captain_of(session, entry, captain_id)
    player = _player_of_entry(session, entry, user_id)
    if player is None or user_id == captain_id:
        msg = "They aren't a player you can remove from your entry."
        raise Refused(msg)
    soft_delete(session, player)


def entry_of_captain(session: Session, tournament: Tournament, captain_id: Snowflake) -> TournamentEntry | None:
    """Return the entry whose team ``captain_id`` captains in ``tournament``, if any."""
    query = (
        alive(TournamentEntry)
        .join(Team, col(TournamentEntry.team_id) == col(Team.id))
        .where(
            TournamentEntry.tournament_id == _id(tournament),
            Team.captain_id == int(captain_id),
            col(Team.deleted_at).is_(None),
        )
    )
    return session.exec(query).first()


# --- The bracket -----------------------------------------------------------------------------------------------------


def start(session: Session, tournament: Tournament, rng: Random) -> None:
    """Form the teams of a solo tournament, then lay out the bracket and give the byes their wins."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started already."
        raise Refused(msg)
    tournament_id = _id(tournament)
    if tournament.mode is TeamMode.SOLO:
        _draw_teams(session, tournament, rng)
    teams = entries_of(session, tournament)
    if len(teams) < 2:  # noqa: PLR2004 - a match needs two teams
        msg = "I need at least two teams."
        raise Refused(msg)
    rng.shuffle(teams)
    rounds = round_count(len(teams))
    for round_ in range(rounds):
        for slot in range(2 ** (rounds - round_ - 1)):
            session.add(TournamentMatch(tournament_id=tournament_id, round=round_, slot=slot))
    session.flush()
    for slot, pairing in enumerate(first_round(teams)):
        match = _match_at(session, tournament, BracketSlot(0, slot))
        match.entry_a_id = _id(pairing.first)
        match.entry_b_id = None if pairing.second is None else _id(pairing.second)
        _move(PhaseContext(session, match), MatchStep.TEAMS_KNOWN)
        if pairing.bye:
            _move(PhaseContext(session, match, winner_id=_id(pairing.first)), MatchStep.BYE)
    tournament.status = TournamentStatus.RUNNING


def _draw_teams(session: Session, tournament: Tournament, rng: Random) -> None:
    """Shuffle a solo tournament's sign-ups into temporary teams, one entry each; the first member drawn captains."""
    signups = signups_of(session, tournament)
    split = split_into_teams([Snowflake(signup.user_id) for signup in signups], tournament.team_size, rng)
    if not split:
        msg = f"I need at least {2 * tournament.team_size} players for two teams of {tournament.team_size}."
        raise Refused(msg)
    teams = create_temporary_teams(session, split, TeamOrigin.SOLO_TOURNAMENT)
    for team, members in zip(teams, split, strict=True):
        team.captain_id = int(members[0])
        session.add(team)
        entry = TournamentEntry(tournament_id=_id(tournament), team_id=_id(team), name=team.name)
        session.add(entry)
        session.flush()
        for user_id in members:
            session.add(EntryPlayer(entry_id=_id(entry), user_id=int(user_id)))


def _match_at(session: Session, tournament: Tournament, at: BracketSlot) -> TournamentMatch:
    """Return the alive match at ``at`` in ``tournament``."""
    query = alive(TournamentMatch).where(
        TournamentMatch.tournament_id == _id(tournament),
        TournamentMatch.round == at.round,
        TournamentMatch.slot == at.slot,
    )
    return session.exec(query).one()


def _decide(ctx: PhaseContext) -> None:
    """Record the winner ``ctx`` names as the match's winner, and move them on to their next match or crown them.

    A bye has no actor, because nobody reports it.
    """
    session, match = ctx.session, ctx.match
    winner_id = _winner(ctx)
    match.winner_id = winner_id
    match.decided_at = utc_now()
    match.decided_by = None if ctx.actor_id is None else int(ctx.actor_id)
    session.add(match)
    tournament = stored(session, Tournament, match.tournament_id, "That tournament is gone.")
    entries = entries_of(session, tournament)
    rounds = round_count(len(entries))
    if match.round == rounds - 1:
        tournament.winner_entry_id = winner_id
        tournament.status = TournamentStatus.FINISHED
        session.add(tournament)
        _end_temporary_teams(session, entries)
        return
    advance_to = next_match(BracketSlot(match.round, match.slot))
    following = _match_at(session, tournament, advance_to.at)
    if advance_to.as_entry_a:
        following.entry_a_id = winner_id
    else:
        following.entry_b_id = winner_id
    if following.entry_a_id is not None and following.entry_b_id is not None:
        _move(PhaseContext(session, following), MatchStep.TEAMS_KNOWN)
    session.add(following)


# --- Phases ----------------------------------------------------------------------------------------------------------


@dataclass
class PhaseContext:
    """What a match step acts on: the session, the match, who took the step, and the winner it names."""

    session: Session
    match: TournamentMatch
    actor_id: Snowflake | None = None
    winner_id: int | None = None


PHASES: StateMachine[MatchPhase, MatchStep, PhaseContext] = StateMachine()
"""Every step a match may take: from which phase, on which step, to which phase, and what the step does."""


def _winner(ctx: PhaseContext) -> int:
    """Return the winner a decision names; a step that decides a match must name one."""
    if ctx.winner_id is None:
        msg = "a decided match needs its winner"
        raise ValueError(msg)
    return ctx.winner_id


def _record(ctx: PhaseContext, kind: MatchEventKind, detail: str = "") -> None:
    """Log ``kind`` in the match's audit trail, unless no member did it: the draw gives a bye, and nobody reports it."""
    if ctx.actor_id is not None:
        record_event(ctx.session, ctx.match, kind, ctx.actor_id, detail)


def _winner_entry(ctx: PhaseContext) -> TournamentEntry:
    """Return the entry ``ctx`` names as the winner; refuse when that team is gone."""
    return stored(ctx.session, TournamentEntry, _winner(ctx), "That team is gone.")


@PHASES.add(MatchPhase.WAITING, event=MatchStep.TEAMS_KNOWN, to_state=MatchPhase.READY)
def _teams_known(ctx: PhaseContext) -> None:
    """Copy each entry's players into the match's lineup once its teams are known."""
    _copy_lineups(ctx.session, ctx.match)


@PHASES.add(MatchPhase.READY, event=MatchStep.ADVANCE, to_state=MatchPhase.BAN)
def _ready_to_ban(ctx: PhaseContext) -> None:
    """Start the bans."""
    _record(ctx, MatchEventKind.PHASE, MatchPhase.BAN.value)


@PHASES.add(MatchPhase.BAN, event=MatchStep.ADVANCE, to_state=MatchPhase.PICK)
def _ban_to_pick(ctx: PhaseContext) -> None:
    """Start the picks."""
    _record(ctx, MatchEventKind.PHASE, MatchPhase.PICK.value)


@PHASES.add(MatchPhase.PICK, event=MatchStep.ADVANCE, to_state=MatchPhase.LIVE)
def _pick_to_live(ctx: PhaseContext) -> None:
    """Start the match, and time it."""
    ctx.match.started_at = utc_now()
    _record(ctx, MatchEventKind.PHASE, MatchPhase.LIVE.value)


@PHASES.add(MatchPhase.READY, event=MatchStep.BYE, to_state=MatchPhase.FINISHED)
def _bye(ctx: PhaseContext) -> None:
    """Give the bye's team the match, without anyone reporting it."""
    _decide(ctx)


@PHASES.add(MatchPhase.LIVE, event=MatchStep.REPORT, to_state=MatchPhase.FINISHED)
def _report_winner(ctx: PhaseContext) -> None:
    """Decide a live match by the reported winner."""
    winner = _winner_entry(ctx)
    _decide(ctx)
    _record(ctx, MatchEventKind.WINNER, winner.name)


@PHASES.add(
    MatchPhase.READY,
    MatchPhase.BAN,
    MatchPhase.PICK,
    MatchPhase.LIVE,
    event=MatchStep.FORFEIT,
    to_state=MatchPhase.FORFEIT,
)
def _forfeit(ctx: PhaseContext) -> None:
    """Decide a match because the other team forfeited, whether or not it is live."""
    winner = _winner_entry(ctx)
    _decide(ctx)
    _record(ctx, MatchEventKind.FORFEIT, winner.name)


def _refusal(phase: MatchPhase, step: MatchStep) -> str:
    """Return what a member is told when ``step`` can't happen to a match in ``phase``."""
    if phase.decided:
        return "This match is decided already."
    if step is MatchStep.REPORT:
        return "The match isn't live yet; a team can forfeit, though."
    if step is MatchStep.ADVANCE and phase is MatchPhase.LIVE:
        return "Report the winner to finish this match."
    return "This match can't move on."


def _move(ctx: PhaseContext, step: MatchStep) -> None:
    """Take ``step`` on ``ctx``'s match, then store the phase it leads to; refuse a step its phase doesn't allow."""
    phase = ctx.match.phase
    if (phase, step) not in PHASES.transitions:
        msg = _refusal(phase, step)
        raise Refused(msg)
    ctx.match.phase = PHASES.handle(ctx, phase, step)
    ctx.session.add(ctx.match)


def following_phase(phase: MatchPhase) -> MatchPhase | None:
    """Return the phase the next button moves a match in ``phase`` to; ``None`` when that step is reporting a winner."""
    for (from_, step), (to, _) in PHASES.transitions.items():
        if from_ is phase and step is MatchStep.ADVANCE:
            return to
    return None


def advance(session: Session, match: TournamentMatch, actor_id: Snowflake) -> None:
    """Move ``match`` on to its next phase: from ready to the bans, the picks, and live."""
    if match.phase is MatchPhase.READY and clashes(session, match):
        msg = "A player is in both lineups; drop them from one side first."
        raise Refused(msg)
    _move(PhaseContext(session, match, actor_id), MatchStep.ADVANCE)


def report(
    session: Session,
    match: TournamentMatch,
    winner_id: int,
    actor_id: Snowflake,
    *,
    forfeit: bool = False,
) -> None:
    """Record ``winner_id`` as the winner of ``match``: by playing it live, or because the other team forfeited."""
    if match.phase.decided:
        msg = "This match is decided already."
        raise Refused(msg)
    if winner_id not in (match.entry_a_id, match.entry_b_id) or None in (match.entry_a_id, match.entry_b_id):
        msg = "That team doesn't play this match."
        raise Refused(msg)
    step = MatchStep.FORFEIT if forfeit else MatchStep.REPORT
    _move(PhaseContext(session, match, actor_id, winner_id), step)


def _end_temporary_teams(session: Session, entries: Sequence[TournamentEntry]) -> None:
    """End the temporary teams behind ``entries`` now; a lasting team stays as it is."""
    now = utc_now()
    for entry in entries:
        team = alive_by_id(session, Team, entry.team_id)
        if team is not None:
            end_team(session, team, now)


def cancel(session: Session, tournament: Tournament) -> None:
    """Call the tournament off: soft-delete it and everything in it, so none of it is seen again."""
    tournament_id = _id(tournament)
    match_ids = [_id(match) for match in matches_of(session, tournament)]
    votes = list(session.exec(alive(MatchVote).where(col(MatchVote.match_id).in_(match_ids))))
    vote_ids = [_id(vote) for vote in votes]
    entries = entries_of(session, tournament)
    entry_ids = [_id(entry) for entry in entries]
    _end_temporary_teams(session, entries)
    rows: list[LifecycleModel] = [
        *session.exec(alive(MatchBallot).where(col(MatchBallot.vote_id).in_(vote_ids))),
        *votes,
        *session.exec(alive(DraftChoice).where(col(DraftChoice.match_id).in_(match_ids))),
        *session.exec(alive(MatchLineup).where(col(MatchLineup.match_id).in_(match_ids))),
        *session.exec(alive(MatchEvent).where(col(MatchEvent.match_id).in_(match_ids))),
        *session.exec(alive(LineupChange).where(col(LineupChange.entry_id).in_(entry_ids))),
        *session.exec(alive(TournamentPost).where(TournamentPost.tournament_id == tournament_id)),
        *session.exec(alive(TournamentMatch).where(TournamentMatch.tournament_id == tournament_id)),
        *session.exec(alive(EntryPlayer).where(col(EntryPlayer.entry_id).in_(entry_ids))),
        *signups_of(session, tournament),
        *entries,
    ]
    for row in rows:
        soft_delete(session, row)
    tournament.status = TournamentStatus.CANCELLED
    soft_delete(session, tournament)


# --- Lineups ---------------------------------------------------------------------------------------------------------


def lineup(session: Session, match: TournamentMatch, entry: TournamentEntry) -> list[Snowflake]:
    """Return the user IDs playing for ``entry`` in ``match``."""
    query = (
        alive(MatchLineup)
        .where(MatchLineup.match_id == _id(match), MatchLineup.entry_id == _id(entry))
        .order_by(col(MatchLineup.id))
    )
    return [Snowflake(row.user_id) for row in session.exec(query)]


def _copy_lineups(session: Session, match: TournamentMatch) -> None:
    """Copy each of the match's entries' current players into its lineup."""
    for entry_id in (match.entry_a_id, match.entry_b_id):
        entry = None if entry_id is None else alive_by_id(session, TournamentEntry, entry_id)
        if entry is None:
            continue
        for user_id in roster(session, entry):
            _lineup_row(session, match, entry, user_id)


def _lineup_row(session: Session, match: TournamentMatch, entry: TournamentEntry, user_id: Snowflake) -> MatchLineup:
    """Return the alive lineup row of ``user_id`` for ``entry`` in ``match``, adding one if there's none."""
    query = alive(MatchLineup).where(
        MatchLineup.match_id == _id(match),
        MatchLineup.entry_id == _id(entry),
        MatchLineup.user_id == int(user_id),
    )
    if (row := session.exec(query).first()) is not None:
        return row
    row = MatchLineup(match_id=_id(match), entry_id=_id(entry), user_id=int(user_id))
    session.add(row)
    return row


def clashes(session: Session, match: TournamentMatch) -> list[Snowflake]:
    """Return the members in both lineups of ``match``, ignoring anonymised ones: their deleted IDs don't match."""
    if match.entry_a_id is None or match.entry_b_id is None:
        return []
    entry_a = alive_by_id(session, TournamentEntry, match.entry_a_id)
    entry_b = alive_by_id(session, TournamentEntry, match.entry_b_id)
    if entry_a is None or entry_b is None:
        return []
    side_b = set(lineup(session, match, entry_b))
    return [user_id for user_id in lineup(session, match, entry_a) if user_id in side_b and int(user_id) != DELETED_MEMBER]


def _next_match(session: Session, tournament: Tournament, entry: TournamentEntry) -> TournamentMatch | None:
    """Return the entry's lowest-round match that isn't decided yet, if it has one."""
    entry_id = _id(entry)
    for match in matches_of(session, tournament):
        if not match.phase.decided and entry_id in (match.entry_a_id, match.entry_b_id):
            return match
    return None


@dataclass(frozen=True)
class LineupRequest:
    """A captain's request to put a member in or take them out of their entry's lineup."""

    captain_id: Snowflake
    user_id: Snowflake
    playing: bool
    reason: str | None = None


def change_lineup(session: Session, tournament: Tournament, entry: TournamentEntry, change: LineupRequest) -> None:
    """Put ``change.user_id`` in (or take them out of) ``entry``'s lineup for its captain, from its next match not yet live.

    The entry's players change, and so does the lineup of its next match while that match is ready or in its draft.
    A live or decided match keeps its lineup. The change is logged, with the match it applied to if any.
    """
    if tournament.status not in ACTIVE:
        msg = "That tournament is over."
        raise Refused(msg)
    team = alive_by_id(session, Team, entry.team_id)
    if team is None or team.captain_id != int(change.captain_id):
        msg = "Only the entry's captain can change its lineup."
        raise Refused(msg)
    entry_id = _id(entry)
    _change_entry_players(session, tournament, entry, change.user_id, playing=change.playing)
    match = _next_match(session, tournament, entry)
    match_id = None
    if match is not None and match.phase in (MatchPhase.READY, MatchPhase.BAN, MatchPhase.PICK):
        match_id = _id(match)
        _change_match_lineup(session, match, entry, change.user_id, playing=change.playing)
    session.add(
        LineupChange(
            entry_id=entry_id,
            match_id=match_id,
            user_id=int(change.user_id),
            playing=change.playing,
            changed_by=int(change.captain_id),
            changed_at=utc_now(),
            reason=change.reason,
        ),
    )


def _change_entry_players(
    session: Session,
    tournament: Tournament,
    entry: TournamentEntry,
    user_id: Snowflake,
    *,
    playing: bool,
) -> None:
    """Add ``user_id`` to the entry's players, or remove them; refuse a full entry, a non-player or the last player."""
    player = _player_of_entry(session, entry, user_id)
    if playing:
        if player is not None:
            msg = "They're in this entry already."
            raise Refused(msg)
        if len(roster(session, entry)) >= tournament.team_size:
            msg = f"Your entry is full: entries have {tournament.team_size} players."
            raise Refused(msg)
        create_or_restore(session, EntryPlayer(entry_id=_id(entry), user_id=int(user_id)))
        return
    if player is None:
        msg = "They aren't playing for your entry."
        raise Refused(msg)
    if len(roster(session, entry)) <= 1:
        msg = "An entry needs at least one player."
        raise Refused(msg)
    soft_delete(session, player)


def _change_match_lineup(
    session: Session,
    match: TournamentMatch,
    entry: TournamentEntry,
    user_id: Snowflake,
    *,
    playing: bool,
) -> None:
    """Add ``user_id`` to the entry's lineup in ``match``, or remove them from it."""
    if playing:
        _lineup_row(session, match, entry, user_id)
        return
    query = alive(MatchLineup).where(
        MatchLineup.match_id == _id(match),
        MatchLineup.entry_id == _id(entry),
        MatchLineup.user_id == int(user_id),
    )
    for row in session.exec(query):
        soft_delete(session, row)


def drop_clash(session: Session, match: TournamentMatch, entry: TournamentEntry, actor_id: Snowflake) -> None:
    """Drop the clashing members from ``entry``'s side of ``match``, recording who did it."""
    if match.phase is not MatchPhase.READY:
        msg = "Clashes are resolved before the draft starts."
        raise Refused(msg)
    entry_id = _id(entry)
    if entry_id not in (match.entry_a_id, match.entry_b_id):
        msg = "That entry doesn't play this match."
        raise Refused(msg)
    match_id = _id(match)
    dropped = set(clashes(session, match))
    if all(user_id in dropped for user_id in lineup(session, match, entry)):
        msg = "An entry needs at least one player."
        raise Refused(msg)
    for row in session.exec(
        alive(MatchLineup).where(MatchLineup.match_id == match_id, MatchLineup.entry_id == entry_id),
    ):
        if Snowflake(row.user_id) in dropped:
            soft_delete(session, row)
    record_event(session, match, MatchEventKind.CLASH_DROPPED, actor_id, entry.name)


# --- Drafts and votes ------------------------------------------------------------------------------------------------


def entry_in_match(session: Session, match: TournamentMatch, user_id: Snowflake) -> TournamentEntry | None:
    """Return the entry in ``match`` whose team ``user_id`` captains, if they captain one of the two."""
    for entry_id in (match.entry_a_id, match.entry_b_id):
        entry = None if entry_id is None else alive_by_id(session, TournamentEntry, entry_id)
        team = None if entry is None else alive_by_id(session, Team, entry.team_id)
        if team is not None and team.captain_id == int(user_id):
            return entry
    return None


def _in_lineup(session: Session, match: TournamentMatch, user_id: Snowflake) -> bool:
    """Whether ``user_id`` is in the lineup of either entry in ``match``, the players actually playing it."""
    query = alive(MatchLineup).where(MatchLineup.match_id == _id(match), MatchLineup.user_id == int(user_id))
    return session.exec(query).first() is not None


def draft(session: Session, match: TournamentMatch, captain_id: Snowflake, kind: DraftKind, value: str) -> None:
    """Record ``captain_id``'s team banning or picking ``value`` in ``match``, during that phase."""
    phase = MatchPhase.BAN if kind is DraftKind.BAN else MatchPhase.PICK
    if match.phase is not phase:
        msg = f"This match isn't in its {kind.value} phase."
        raise Refused(msg)
    entry = entry_in_match(session, match, captain_id)
    if entry is None:
        msg = f"Only a captain playing this match can {kind.value}."
        raise Refused(msg)
    taken = session.exec(alive(DraftChoice).where(DraftChoice.match_id == match.id, DraftChoice.value == value)).first()
    if taken is not None:
        msg = f"{value} is {'banned' if taken.kind is DraftKind.BAN else 'picked'} already."
        raise Refused(msg)
    session.add(DraftChoice(match_id=_id(match), entry_id=_id(entry), kind=kind, value=value))
    record_event(session, match, MatchEventKind.DRAFT, captain_id, f"{kind.value}: {value}")


def drafts_of(session: Session, match: TournamentMatch) -> list[DraftChoice]:
    """Return the bans and picks made in the match, in the order they were made."""
    return list(session.exec(alive(DraftChoice).where(DraftChoice.match_id == _id(match)).order_by(col(DraftChoice.id))))


def open_vote(
    session: Session,
    match: TournamentMatch,
    question: str,
    options: Sequence[str],
    actor_id: Snowflake,
) -> MatchVote:
    """Open a vote on ``question`` among ``options`` for the players of ``match``, recording who opened it."""
    if match.phase.decided:
        msg = "This match is decided already."
        raise Refused(msg)
    if not valid_options(options):
        msg = "Give between 2 and 10 different answers, separated by commas, each short enough for a button."
        raise Refused(msg)
    vote = MatchVote(match_id=_id(match), question=question, options="\n".join(options))
    session.add(vote)
    session.flush()
    record_event(session, match, MatchEventKind.VOTE_OPENED, actor_id, question)
    return vote


def close_vote(session: Session, vote: MatchVote, actor_id: Snowflake) -> None:
    """Close ``vote`` so it takes no more answers, recording who closed it."""
    vote.open = False
    session.add(vote)
    match = stored(session, TournamentMatch, vote.match_id, "This vote is gone.")
    record_event(session, match, MatchEventKind.VOTE_CLOSED, actor_id, vote.question)


def cast(session: Session, vote: MatchVote, user_id: Snowflake, choice: int) -> None:
    """Record ``user_id``'s answer ``choice`` to ``vote``, replacing their earlier one."""
    if not vote.open:
        msg = "This vote is closed."
        raise Refused(msg)
    match = alive_by_id(session, TournamentMatch, vote.match_id)
    if match is None or not _in_lineup(session, match, user_id):
        msg = "Only the players of this match can vote."
        raise Refused(msg)
    upsert(session, MatchBallot(vote_id=_id(vote), user_id=int(user_id), choice=choice))


def choices_of(session: Session, vote: MatchVote) -> list[int]:
    """Return every answer given to the vote."""
    return [ballot.choice for ballot in session.exec(alive(MatchBallot).where(MatchBallot.vote_id == _id(vote)))]
