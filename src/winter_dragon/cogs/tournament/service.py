"""What can happen to a tournament: signing up, forming teams, running the bracket, drafting and voting.

Each action takes an open session and leaves committing to the caller. An action that isn't allowed raises
:class:`~wd_errors.Refused` saying why, for the player; the caller then drops the session's changes.
"""

lazy from typing import TYPE_CHECKING, override

from sqlmodel import Session, col, select
lazy from sqlalchemy import exists
lazy from sqlalchemy.orm import aliased
lazy from wd_db.extension.lifecycle import alive, alive_by_id, create_or_restore, soft_delete, upsert
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from winter_dragon.cogs.team.models import Team, TeamKind, TeamOrigin
lazy from winter_dragon.cogs.team.service import create_temporary_teams, end_team, membership
lazy from winter_dragon.cogs.team.split import split_into_teams
lazy from winter_dragon.member_hidden import MemberHiddenHook, RemovedRows

lazy from .bracket import first_round, next_match, round_count, valid_options
lazy from .models import (
    ACTIVE,
    DraftChoice,
    DraftKind,
    EntryPlayer,
    MatchBallot,
    MatchLineup,
    MatchPhase,
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
    lazy from random import Random

    lazy from sqlmodel.sql.expression import SelectOfScalar
    lazy from wd_db.extension.lifecycle import LifecycleModel
    lazy from wd_discord.snowflake import Snowflake


def visible_tournaments(
    session: Session,
    guild_id: Snowflake,
    user_id: Snowflake,
    channel_id: Snowflake | None,
) -> Generator[Tournament]:
    """Yield the guild's tournaments that aren't over and that ``user_id`` organises or signed up for.

    Also yields the ones posted in ``channel_id``, by name.
    """
    query = (
        alive(Tournament)
        .where(Tournament.guild_id == int(guild_id), col(Tournament.status).in_(ACTIVE))
        .order_by(col(Tournament.name))
    )
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


def posts_of(session: Session, tournament_id: int) -> Generator[TournamentPost]:
    """Yield the tournament's posts."""
    yield from session.exec(
        alive(TournamentPost).where(TournamentPost.tournament_id == tournament_id).order_by(col(TournamentPost.id)),
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


def signups_of(session: Session, tournament_id: int) -> list[TournamentSignup]:
    """Return everyone signed up alone for the tournament, in sign-up order."""
    query = alive(TournamentSignup).where(TournamentSignup.tournament_id == tournament_id).order_by(col(TournamentSignup.id))
    return list(session.exec(query))


def signup_of(session: Session, tournament_id: int, user_id: Snowflake) -> TournamentSignup | None:
    """Return the user's solo sign-up for the tournament, if any."""
    query = alive(TournamentSignup).where(
        TournamentSignup.tournament_id == tournament_id,
        TournamentSignup.user_id == int(user_id),
    )
    return session.exec(query).first()


def entries_of(session: Session, tournament_id: int) -> list[TournamentEntry]:
    """Return the tournament's teams, in the order they were formed."""
    query = alive(TournamentEntry).where(TournamentEntry.tournament_id == tournament_id).order_by(col(TournamentEntry.id))
    return list(session.exec(query))


def roster(session: Session, entry_id: int) -> list[int]:
    """Return the user IDs of the entry's players."""
    return [player.user_id for player in _players_of_entry(session, entry_id)]


def _players_of_entry(session: Session, entry_id: int) -> list[EntryPlayer]:
    """Return the entry's player rows, in the order they were added."""
    return list(session.exec(alive(EntryPlayer).where(EntryPlayer.entry_id == entry_id).order_by(col(EntryPlayer.id))))


def _player_of_entry(session: Session, entry_id: int, user_id: Snowflake) -> EntryPlayer | None:
    """Return the player row of ``user_id`` in the entry, if they play for it."""
    query = alive(EntryPlayer).where(EntryPlayer.entry_id == entry_id, EntryPlayer.user_id == int(user_id))
    return session.exec(query).first()


def matches_of(session: Session, tournament_id: int) -> list[TournamentMatch]:
    """Return the tournament's matches, round by round, top to bottom."""
    query = (
        alive(TournamentMatch)
        .where(TournamentMatch.tournament_id == tournament_id)
        .order_by(col(TournamentMatch.round), col(TournamentMatch.slot))
    )
    return list(session.exec(query))


def _id(record: Tournament | Team | TournamentEntry | TournamentMatch | MatchVote) -> int:
    """Return a stored record's ID."""
    if record.id is None:
        msg = f"{type(record).__name__} isn't stored yet"
        raise ValueError(msg)
    return record.id


# --- Sign-up ---------------------------------------------------------------------------------------------------------


def sign_up(session: Session, tournament: Tournament, user_id: Snowflake) -> None:
    """Sign ``user_id`` up for a solo tournament."""
    if tournament.status is not TournamentStatus.SIGNUP:
        msg = "Sign-up for this tournament is closed."
        raise Refused(msg)
    if tournament.mode is not TeamMode.SOLO:
        msg = "Teams sign up for this tournament; a captain enters a team with /tournament enter."
        raise Refused(msg)
    if signup_of(session, _id(tournament), user_id) is not None:
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
    tournament_id = _id(tournament)
    if tournament.mode is TeamMode.SOLO:
        signup = signup_of(session, tournament_id, user_id)
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
    for player in _players_of_entry(session, _id(entry)):
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
                if entry is not None and not roster(session, player.entry_id):
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
    if any(entry.team_id == _id(team) for entry in entries_of(session, _id(tournament))):
        msg = "That team has entered already."
        raise Refused(msg)
    if any(entry.name.casefold() == team.name.casefold() for entry in entries_of(session, _id(tournament))):
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
    if membership(session, team, int(user_id)) is None:
        msg = "They aren't in your team."
        raise Refused(msg)
    if _player_of_entry(session, _id(entry), user_id) is not None:
        msg = "They're in this entry already."
        raise Refused(msg)
    if len(roster(session, _id(entry))) >= tournament.team_size:
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
    player = _player_of_entry(session, _id(entry), user_id)
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
    teams = entries_of(session, tournament_id)
    if len(teams) < 2:  # noqa: PLR2004 - a match needs two teams
        msg = "I need at least two teams."
        raise Refused(msg)
    entry_ids = [_id(team) for team in teams]
    rng.shuffle(entry_ids)
    rounds = round_count(len(entry_ids))
    for round_ in range(rounds):
        for slot in range(2 ** (rounds - round_ - 1)):
            session.add(TournamentMatch(tournament_id=tournament_id, round=round_, slot=slot))
    session.flush()
    for slot, (team_a, team_b) in enumerate(first_round(entry_ids)):
        match = _match_at(session, tournament_id, 0, slot)
        match.entry_a_id, match.entry_b_id = team_a, team_b
        match.phase = MatchPhase.READY
        _copy_lineups(session, match)
        if team_b is None:
            _decide(session, tournament, match, team_a, MatchPhase.FINISHED)
    tournament.status = TournamentStatus.RUNNING


def _draw_teams(session: Session, tournament: Tournament, rng: Random) -> None:
    """Shuffle a solo tournament's sign-ups into temporary teams, one entry each; the first member drawn captains."""
    signups = signups_of(session, _id(tournament))
    split = split_into_teams([signup.user_id for signup in signups], tournament.team_size, rng)
    if not split:
        msg = f"I need at least {2 * tournament.team_size} players for two teams of {tournament.team_size}."
        raise Refused(msg)
    teams = create_temporary_teams(session, split, TeamOrigin.SOLO_TOURNAMENT)
    for team, members in zip(teams, split, strict=True):
        team.captain_id = members[0]
        session.add(team)
        entry = TournamentEntry(tournament_id=_id(tournament), team_id=_id(team), name=team.name)
        session.add(entry)
        session.flush()
        for user_id in members:
            session.add(EntryPlayer(entry_id=_id(entry), user_id=user_id))


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
    entries = entries_of(session, _id(tournament))
    rounds = round_count(len(entries))
    if match.round == rounds - 1:
        tournament.winner_entry_id = winner_id
        tournament.status = TournamentStatus.FINISHED
        session.add(tournament)
        _end_temporary_teams(session, entries)
        return
    round_, slot, as_team_a = next_match(match.round, match.slot)
    following = _match_at(session, _id(tournament), round_, slot)
    if as_team_a:
        following.entry_a_id = winner_id
    else:
        following.entry_b_id = winner_id
    if following.entry_a_id is not None and following.entry_b_id is not None:
        following.phase = MatchPhase.READY
        _copy_lineups(session, following)
    session.add(following)


def advance(session: Session, match: TournamentMatch) -> None:
    """Move ``match`` on to its next phase: from ready to the bans, the picks, and live."""
    if match.phase is MatchPhase.READY and clashes(session, match):
        msg = "A player is in both lineups; drop them from one side first."
        raise Refused(msg)
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
    if winner_id not in (match.entry_a_id, match.entry_b_id) or None in (match.entry_a_id, match.entry_b_id):
        msg = "That team doesn't play this match."
        raise Refused(msg)
    if not forfeit and match.phase is not MatchPhase.LIVE:
        msg = "The match isn't live yet; a team can forfeit, though."
        raise Refused(msg)
    _decide(session, tournament, match, winner_id, MatchPhase.FORFEIT if forfeit else MatchPhase.FINISHED)


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
    match_ids = [_id(match) for match in matches_of(session, tournament_id)]
    votes = list(session.exec(alive(MatchVote).where(col(MatchVote.match_id).in_(match_ids))))
    vote_ids = [_id(vote) for vote in votes]
    entries = entries_of(session, tournament_id)
    entry_ids = [_id(entry) for entry in entries]
    _end_temporary_teams(session, entries)
    rows: list[LifecycleModel] = [
        *session.exec(alive(MatchBallot).where(col(MatchBallot.vote_id).in_(vote_ids))),
        *votes,
        *session.exec(alive(DraftChoice).where(col(DraftChoice.match_id).in_(match_ids))),
        *session.exec(alive(MatchLineup).where(col(MatchLineup.match_id).in_(match_ids))),
        *session.exec(alive(TournamentMatch).where(TournamentMatch.tournament_id == tournament_id)),
        *session.exec(alive(EntryPlayer).where(col(EntryPlayer.entry_id).in_(entry_ids))),
        *signups_of(session, tournament_id),
        *entries,
    ]
    for row in rows:
        soft_delete(session, row)
    tournament.status = TournamentStatus.CANCELLED
    soft_delete(session, tournament)


# --- Lineups ---------------------------------------------------------------------------------------------------------


def lineup(session: Session, match_id: int, entry_id: int) -> list[int]:
    """Return the user IDs playing for ``entry_id`` in match ``match_id``."""
    query = (
        alive(MatchLineup)
        .where(MatchLineup.match_id == match_id, MatchLineup.entry_id == entry_id)
        .order_by(col(MatchLineup.id))
    )
    return [row.user_id for row in session.exec(query)]


def _copy_lineups(session: Session, match: TournamentMatch) -> None:
    """Copy each of the match's entries' current players into its lineup."""
    for entry_id in (match.entry_a_id, match.entry_b_id):
        if entry_id is None:
            continue
        for user_id in roster(session, entry_id):
            create_or_restore(session, MatchLineup(match_id=_id(match), entry_id=entry_id, user_id=user_id))


def clashes(session: Session, match: TournamentMatch) -> list[int]:
    """Return the members in both lineups of ``match``."""
    if match.entry_a_id is None or match.entry_b_id is None:
        return []
    match_id = _id(match)
    side_b = set(lineup(session, match_id, match.entry_b_id))
    return [user_id for user_id in lineup(session, match_id, match.entry_a_id) if user_id in side_b]


def _next_match(session: Session, tournament: Tournament, entry: TournamentEntry) -> TournamentMatch | None:
    """Return the entry's lowest-round match that isn't decided yet, if it has one."""
    entry_id = _id(entry)
    for match in matches_of(session, _id(tournament)):
        if not match.phase.decided and entry_id in (match.entry_a_id, match.entry_b_id):
            return match
    return None


def change_lineup(  # noqa: PLR0913 - the brief fixes these parameters: the tournament, the entry, its captain, the member and the direction
    session: Session,
    tournament: Tournament,
    entry: TournamentEntry,
    captain_id: Snowflake,
    user_id: Snowflake,
    *,
    playing: bool,
) -> None:
    """Put ``user_id`` in (or take them out of) ``entry``'s lineup for its captain, from its next match not yet live.

    The entry's players change, and so does the lineup of its next match while that match is ready or in its draft.
    A live or decided match keeps its lineup.
    """
    if tournament.status not in ACTIVE:
        msg = "That tournament is over."
        raise Refused(msg)
    team = alive_by_id(session, Team, entry.team_id)
    if team is None or team.captain_id != int(captain_id):
        msg = "Only the entry's captain can change its lineup."
        raise Refused(msg)
    entry_id = _id(entry)
    _change_entry_players(session, tournament, entry_id, user_id, playing=playing)
    match = _next_match(session, tournament, entry)
    if match is not None and match.phase in (MatchPhase.READY, MatchPhase.BAN, MatchPhase.PICK):
        _change_match_lineup(session, _id(match), entry_id, user_id, playing=playing)


def _change_entry_players(
    session: Session,
    tournament: Tournament,
    entry_id: int,
    user_id: Snowflake,
    *,
    playing: bool,
) -> None:
    """Add ``user_id`` to the entry's players, or remove them; refuse a full entry, a non-player or the last player."""
    player = _player_of_entry(session, entry_id, user_id)
    if playing:
        if player is not None:
            msg = "They're in this entry already."
            raise Refused(msg)
        if len(roster(session, entry_id)) >= tournament.team_size:
            msg = f"Your entry is full: entries have {tournament.team_size} players."
            raise Refused(msg)
        create_or_restore(session, EntryPlayer(entry_id=entry_id, user_id=int(user_id)))
        return
    if player is None:
        msg = "They aren't playing for your entry."
        raise Refused(msg)
    if len(roster(session, entry_id)) <= 1:
        msg = "An entry needs at least one player."
        raise Refused(msg)
    soft_delete(session, player)


def _change_match_lineup(session: Session, match_id: int, entry_id: int, user_id: Snowflake, *, playing: bool) -> None:
    """Add ``user_id`` to the entry's lineup in match ``match_id``, or remove them from it."""
    if playing:
        create_or_restore(session, MatchLineup(match_id=match_id, entry_id=entry_id, user_id=int(user_id)))
        return
    query = alive(MatchLineup).where(
        MatchLineup.match_id == match_id,
        MatchLineup.entry_id == entry_id,
        MatchLineup.user_id == int(user_id),
    )
    for row in session.exec(query):
        soft_delete(session, row)


def drop_clash(session: Session, match: TournamentMatch, entry: TournamentEntry) -> None:
    """Drop the clashing members from ``entry``'s side of ``match``."""
    if match.phase is not MatchPhase.READY:
        msg = "Clashes are resolved before the draft starts."
        raise Refused(msg)
    entry_id = _id(entry)
    if entry_id not in (match.entry_a_id, match.entry_b_id):
        msg = "That entry doesn't play this match."
        raise Refused(msg)
    match_id = _id(match)
    dropped = set(clashes(session, match))
    if all(user_id in dropped for user_id in lineup(session, match_id, entry_id)):
        msg = "An entry needs at least one player."
        raise Refused(msg)
    for row in session.exec(
        alive(MatchLineup).where(MatchLineup.match_id == match_id, MatchLineup.entry_id == entry_id),
    ):
        if row.user_id in dropped:
            soft_delete(session, row)


# --- Drafts and votes ------------------------------------------------------------------------------------------------


def entry_in_match(session: Session, match: TournamentMatch, user_id: Snowflake) -> TournamentEntry | None:
    """Return the entry in ``match`` whose team ``user_id`` captains, if they captain one of the two."""
    for entry_id in (match.entry_a_id, match.entry_b_id):
        entry = None if entry_id is None else alive_by_id(session, TournamentEntry, entry_id)
        team = None if entry is None else alive_by_id(session, Team, entry.team_id)
        if team is not None and team.captain_id == int(user_id):
            return entry
    return None


def _plays_in(session: Session, match: TournamentMatch, user_id: Snowflake) -> bool:
    """Whether ``user_id`` is a player of either entry in ``match``."""
    return any(
        entry_id is not None and _player_of_entry(session, entry_id, user_id) is not None
        for entry_id in (match.entry_a_id, match.entry_b_id)
    )


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


def cast(session: Session, vote: MatchVote, user_id: Snowflake, choice: int) -> None:
    """Record ``user_id``'s answer ``choice`` to ``vote``, replacing their earlier one."""
    if not vote.open:
        msg = "This vote is closed."
        raise Refused(msg)
    match = alive_by_id(session, TournamentMatch, vote.match_id)
    if match is None or not _plays_in(session, match, user_id):
        msg = "Only the players of this match can vote."
        raise Refused(msg)
    upsert(session, MatchBallot(vote_id=_id(vote), user_id=int(user_id), choice=choice))


def choices_of(session: Session, vote_id: int) -> list[int]:
    """Return every answer given to the vote."""
    return [ballot.choice for ballot in session.exec(alive(MatchBallot).where(MatchBallot.vote_id == vote_id))]
