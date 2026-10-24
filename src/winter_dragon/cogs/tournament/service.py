"""What can happen to a tournament: signing up, forming teams, running the bracket, drafting and voting.

Each action takes an open session and leaves committing to the caller. An action that isn't allowed raises
:class:`~wd_errors.Refused` saying why, for the player; the caller then drops the session's changes.
"""

lazy from typing import TYPE_CHECKING

from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive, create_or_restore, soft_delete
lazy from wd_errors import Refused

lazy from .bracket import first_round, next_match, round_count, split_into_teams, valid_options
lazy from .models import (
    ACTIVE,
    DraftChoice,
    DraftKind,
    MatchBallot,
    MatchPhase,
    MatchVote,
    TeamMode,
    Tournament,
    TournamentMatch,
    TournamentPlayer,
    TournamentStatus,
    TournamentTeam,
)


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence
    lazy from random import Random

    lazy from wd_db.extension.lifecycle import LifecycleModel


def alive_record[M: LifecycleModel](session: Session, model: type[M], record_id: int | None) -> M | None:
    """Return the ``model`` row ``record_id``, unless there's none or it's soft-deleted."""
    return session.exec(alive(model).where(model.id == record_id)).first()


def active_tournament(session: Session, guild_id: int) -> Tournament | None:
    """Return the guild's tournament that isn't over, if it has one."""
    query = alive(Tournament).where(Tournament.guild_id == guild_id, col(Tournament.status).in_(ACTIVE))
    return session.exec(query).first()


def players_of(session: Session, tournament_id: int) -> list[TournamentPlayer]:
    """Return everyone signed up for the tournament, in sign-up order."""
    query = alive(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament_id).order_by(col(TournamentPlayer.id))
    return list(session.exec(query))


def player_of(session: Session, tournament_id: int, user_id: int) -> TournamentPlayer | None:
    """Return the user's sign-up for the tournament, if any."""
    query = alive(TournamentPlayer).where(TournamentPlayer.tournament_id == tournament_id, TournamentPlayer.user_id == user_id)
    return session.exec(query).first()


def teams_of(session: Session, tournament_id: int) -> list[TournamentTeam]:
    """Return the tournament's teams, in the order they were formed."""
    query = alive(TournamentTeam).where(TournamentTeam.tournament_id == tournament_id).order_by(col(TournamentTeam.id))
    return list(session.exec(query))


def roster(session: Session, team_id: int) -> list[int]:
    """Return the user IDs of the team's players."""
    return [player.user_id for player in session.exec(alive(TournamentPlayer).where(TournamentPlayer.team_id == team_id))]


def matches_of(session: Session, tournament_id: int) -> list[TournamentMatch]:
    """Return the tournament's matches, round by round, top to bottom."""
    query = (
        alive(TournamentMatch)
        .where(TournamentMatch.tournament_id == tournament_id)
        .order_by(col(TournamentMatch.round), col(TournamentMatch.slot))
    )
    return list(session.exec(query))


def _id(record: Tournament | TournamentTeam | TournamentMatch | MatchVote) -> int:
    """Return a stored record's ID."""
    if record.id is None:
        msg = f"{type(record).__name__} isn't stored yet"
        raise ValueError(msg)
    return record.id


# --- Sign-up ---------------------------------------------------------------------------------------------------------


def sign_up(session: Session, tournament: Tournament, user_id: int) -> None:
    """Sign ``user_id`` up for a solo tournament."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "Sign-up for this tournament is closed."
        raise Refused(msg)
    if tournament.mode is not TeamMode.SOLO:
        msg = "Teams sign up for this tournament; ask a captain to add you, or register a team."
        raise Refused(msg)
    if player_of(session, _id(tournament), user_id) is not None:
        msg = "You're signed up already."
        raise Refused(msg)
    create_or_restore(session, TournamentPlayer(tournament_id=_id(tournament), user_id=user_id))


def open_signups_of(session: Session, user_id: int) -> Generator[Tournament]:
    """Yield the tournaments ``user_id`` is signed up for that haven't started."""
    query = (
        alive(Tournament)
        .join(TournamentPlayer, col(TournamentPlayer.tournament_id) == col(Tournament.id))
        .where(
            TournamentPlayer.user_id == user_id,
            col(TournamentPlayer.deleted_at).is_(None),
            Tournament.status == TournamentStatus.SIGNUP,
        )
    )
    yield from session.exec(query)


def withdraw(session: Session, tournament: Tournament, user_id: int) -> None:
    """Take ``user_id`` out of the tournament before it starts; a captain leaving disbands their team."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started; ask the organiser to forfeit your matches instead."
        raise Refused(msg)
    player = player_of(session, _id(tournament), user_id)
    if player is None:
        msg = "You aren't signed up."
        raise Refused(msg)
    team = alive_record(session, TournamentTeam, player.team_id)
    if team is not None and team.captain_id == user_id:
        for teammate in session.exec(alive(TournamentPlayer).where(TournamentPlayer.team_id == team.id)).all():
            soft_delete(session, teammate)
        soft_delete(session, team)
    else:
        soft_delete(session, player)


def create_team(session: Session, tournament: Tournament, captain_id: int, name: str) -> None:
    """Register the team ``name`` with ``captain_id`` as its captain and first player."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "Sign-up for this tournament is closed."
        raise Refused(msg)
    if tournament.mode is not TeamMode.CAPTAINS:
        msg = "Players sign up alone for this tournament, and are put in teams when it starts."
        raise Refused(msg)
    if player_of(session, _id(tournament), captain_id) is not None:
        msg = "You're in this tournament already."
        raise Refused(msg)
    if any(team.name.casefold() == name.casefold() for team in teams_of(session, _id(tournament))):
        msg = "A team has that name already."
        raise Refused(msg)
    team = TournamentTeam(tournament_id=_id(tournament), name=name, captain_id=captain_id)
    session.add(team)
    session.flush()
    create_or_restore(session, TournamentPlayer(tournament_id=_id(tournament), user_id=captain_id, team_id=team.id))


def _captained(session: Session, tournament: Tournament, captain_id: int) -> TournamentTeam | None:
    query = alive(TournamentTeam).where(TournamentTeam.tournament_id == tournament.id, TournamentTeam.captain_id == captain_id)
    return session.exec(query).first()


def add_to_team(session: Session, tournament: Tournament, captain_id: int, user_id: int) -> None:
    """Add ``user_id`` to the team ``captain_id`` captains."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "Sign-up for this tournament is closed."
        raise Refused(msg)
    team = _captained(session, tournament, captain_id)
    if team is None:
        msg = "Only a team's captain can add players to it."
        raise Refused(msg)
    if player_of(session, _id(tournament), user_id) is not None:
        msg = "They're in this tournament already."
        raise Refused(msg)
    if len(roster(session, _id(team))) >= tournament.team_size:
        msg = f"Your team is full: teams have {tournament.team_size} players."
        raise Refused(msg)
    create_or_restore(session, TournamentPlayer(tournament_id=_id(tournament), user_id=user_id, team_id=team.id))


def remove_from_team(session: Session, tournament: Tournament, captain_id: int, user_id: int) -> None:
    """Take ``user_id`` off the team ``captain_id`` captains."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started; teams can't change any more."
        raise Refused(msg)
    team = _captained(session, tournament, captain_id)
    if team is None:
        msg = "Only a team's captain can remove players from it."
        raise Refused(msg)
    player = player_of(session, _id(tournament), user_id)
    if player is None or player.team_id != team.id or user_id == captain_id:
        msg = "They aren't a player you can remove from your team."
        raise Refused(msg)
    soft_delete(session, player)


# --- The bracket -----------------------------------------------------------------------------------------------------


def start(session: Session, tournament: Tournament, rng: Random) -> None:
    """Form the teams of a solo tournament, then lay out the bracket and give the byes their wins."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "The tournament has started already."
        raise Refused(msg)
    tournament_id = _id(tournament)
    if tournament.mode is TeamMode.SOLO:
        _draw_teams(session, tournament, rng)
    teams = teams_of(session, tournament_id)
    if len(teams) < 2:  # noqa: PLR2004 - a match needs two teams
        msg = "I need at least two teams."
        raise Refused(msg)
    team_ids = [_id(team) for team in teams]
    rng.shuffle(team_ids)
    rounds = round_count(len(team_ids))
    for round_ in range(rounds):
        for slot in range(2 ** (rounds - round_ - 1)):
            session.add(TournamentMatch(tournament_id=tournament_id, round=round_, slot=slot))
    session.flush()
    for slot, (team_a, team_b) in enumerate(first_round(team_ids)):
        match = _match_at(session, tournament_id, 0, slot)
        match.team_a_id, match.team_b_id = team_a, team_b
        match.phase = MatchPhase.READY
        if team_b is None:
            _decide(session, tournament, match, team_a, MatchPhase.FINISHED)
    tournament.status = TournamentStatus.RUNNING


def _draw_teams(session: Session, tournament: Tournament, rng: Random) -> None:
    """Shuffle a solo tournament's players into teams; the first player drawn into a team captains it."""
    players = players_of(session, _id(tournament))
    split = split_into_teams([player.user_id for player in players], tournament.team_size, rng)
    if not split:
        msg = f"I need at least {2 * tournament.team_size} players for two teams of {tournament.team_size}."
        raise Refused(msg)
    by_user = {player.user_id: player for player in players}
    for number, members in enumerate(split, 1):
        team = TournamentTeam(tournament_id=_id(tournament), name=f"Team {number}", captain_id=members[0])
        session.add(team)
        session.flush()
        for user_id in members:
            by_user[user_id].team_id = team.id


def _match_at(session: Session, tournament_id: int, round_: int, slot: int) -> TournamentMatch:
    query = alive(TournamentMatch).where(
        TournamentMatch.tournament_id == tournament_id,
        TournamentMatch.round == round_,
        TournamentMatch.slot == slot,
    )
    return session.exec(query).one()


def _decide(session: Session, tournament: Tournament, match: TournamentMatch, winner_id: int, phase: MatchPhase) -> None:
    """Record ``winner_id`` as the match's winner, and move them on to their next match or crown them."""
    match.winner_id = winner_id
    match.phase = phase
    session.add(match)
    rounds = round_count(len(teams_of(session, _id(tournament))))
    if match.round == rounds - 1:
        tournament.winner_team_id = winner_id
        tournament.status = TournamentStatus.FINISHED
        session.add(tournament)
        return
    round_, slot, as_team_a = next_match(match.round, match.slot)
    following = _match_at(session, _id(tournament), round_, slot)
    if as_team_a:
        following.team_a_id = winner_id
    else:
        following.team_b_id = winner_id
    if following.team_a_id is not None and following.team_b_id is not None:
        following.phase = MatchPhase.READY
    session.add(following)


def advance(session: Session, match: TournamentMatch) -> None:
    """Move ``match`` on to its next phase: from ready to the bans, the picks, and live."""
    following = match.phase.next
    if following is None:
        msg = "Report the winner to finish this match." if match.phase is MatchPhase.LIVE else "This match can't move on."
        raise Refused(msg)
    match.phase = following
    session.add(match)


def report(
    session: Session,
    tournament: Tournament,
    match: TournamentMatch,
    winner_id: int,
    *,
    forfeit: bool = False,
) -> None:
    """Record ``winner_id`` as the winner of ``match``: by playing it live, or because the other team forfeited."""
    if match.phase.decided:
        msg = "This match is decided already."
        raise Refused(msg)
    if winner_id not in (match.team_a_id, match.team_b_id) or None in (match.team_a_id, match.team_b_id):
        msg = "That team doesn't play this match."
        raise Refused(msg)
    if not forfeit and match.phase is not MatchPhase.LIVE:
        msg = "The match isn't live yet; a team can forfeit, though."
        raise Refused(msg)
    _decide(session, tournament, match, winner_id, MatchPhase.FORFEIT if forfeit else MatchPhase.FINISHED)


def cancel(session: Session, tournament: Tournament) -> None:
    """Call the tournament off: soft-delete it and everything in it, so none of it is seen again."""
    tournament_id = _id(tournament)
    match_ids = [_id(match) for match in matches_of(session, tournament_id)]
    votes = list(session.exec(alive(MatchVote).where(col(MatchVote.match_id).in_(match_ids))))
    vote_ids = [_id(vote) for vote in votes]
    rows: list[LifecycleModel] = [
        *session.exec(alive(MatchBallot).where(col(MatchBallot.vote_id).in_(vote_ids))),
        *votes,
        *session.exec(alive(DraftChoice).where(col(DraftChoice.match_id).in_(match_ids))),
        *session.exec(alive(TournamentMatch).where(TournamentMatch.tournament_id == tournament_id)),
        *players_of(session, tournament_id),
        *teams_of(session, tournament_id),
    ]
    for row in rows:
        soft_delete(session, row)
    tournament.status = TournamentStatus.CANCELLED
    soft_delete(session, tournament)


# --- Drafts and votes ------------------------------------------------------------------------------------------------


def team_in_match(session: Session, match: TournamentMatch, user_id: int) -> TournamentTeam | None:
    """Return the team ``user_id`` plays for in ``match``, if they play in it."""
    for team_id in (match.team_a_id, match.team_b_id):
        if team_id is not None and user_id in roster(session, team_id):
            return alive_record(session, TournamentTeam, team_id)
    return None


def draft(session: Session, match: TournamentMatch, captain_id: int, kind: DraftKind, value: str) -> None:
    """Record ``captain_id``'s team banning or picking ``value`` in ``match``, during that phase."""
    phase = MatchPhase.BAN if kind is DraftKind.BAN else MatchPhase.PICK
    if match.phase is not phase:
        msg = f"This match isn't in its {kind.value} phase."
        raise Refused(msg)
    team = team_in_match(session, match, captain_id)
    if team is None or team.captain_id != captain_id:
        msg = f"Only a captain playing this match can {kind.value}."
        raise Refused(msg)
    taken = session.exec(alive(DraftChoice).where(DraftChoice.match_id == match.id, DraftChoice.value == value)).first()
    if taken is not None:
        msg = f"{value} is {'banned' if taken.kind is DraftKind.BAN else 'picked'} already."
        raise Refused(msg)
    session.add(DraftChoice(match_id=_id(match), team_id=_id(team), kind=kind, value=value))


def drafts_of(session: Session, match_id: int) -> list[DraftChoice]:
    """Return the bans and picks made in the match, in the order they were made."""
    return list(session.exec(alive(DraftChoice).where(DraftChoice.match_id == match_id).order_by(col(DraftChoice.id))))


def open_vote(session: Session, match: TournamentMatch, question: str, options: Sequence[str]) -> MatchVote:
    """Open a vote on ``question`` among ``options`` for the players of ``match``."""
    if match.phase.decided:
        msg = "This match is decided already."
        raise Refused(msg)
    if not valid_options(options):
        msg = "Give between 2 and 10 different answers, separated by commas, each short enough for a button."
        raise Refused(msg)
    vote = MatchVote(match_id=_id(match), question=question, options="\n".join(options))
    session.add(vote)
    session.flush()
    return vote


def cast(session: Session, vote: MatchVote, user_id: int, choice: int) -> None:
    """Record ``user_id``'s answer ``choice`` to ``vote``, replacing their earlier one."""
    if not vote.open:
        msg = "This vote is closed."
        raise Refused(msg)
    match = alive_record(session, TournamentMatch, vote.match_id)
    if match is None or team_in_match(session, match, user_id) is None:
        msg = "Only the players of this match can vote."
        raise Refused(msg)
    ballot = session.exec(alive(MatchBallot).where(MatchBallot.vote_id == vote.id, MatchBallot.user_id == user_id)).first()
    if ballot is None:
        create_or_restore(session, MatchBallot(vote_id=_id(vote), user_id=user_id, choice=choice))
        return
    ballot.choice = choice
    session.add(ballot)


def choices_of(session: Session, vote_id: int) -> list[int]:
    """Return every answer given to the vote."""
    return [ballot.choice for ballot in session.exec(alive(MatchBallot).where(MatchBallot.vote_id == vote_id))]
