"""The Profile's teams page: the member's lasting teams, with their captain, members, and the tournaments each one entered."""

lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive
lazy from wd_discord.snowflake import Snowflake

lazy from winter_dragon.cogs.team.models import Team, TeamKind
lazy from winter_dragon.cogs.team.service import members_of, teams_of
lazy from winter_dragon.cogs.tournament.models import Tournament, TournamentEntry, TournamentStatus
lazy from winter_dragon.web.profile import ProfileContext, profile_page


if TYPE_CHECKING:
    from winter_dragon.web.references import ReferenceLink


@dataclass(frozen=True)
class EntryRow:
    """One tournament a team entered, and how it went for the team."""

    tournament: str
    result: str


@dataclass(frozen=True)
class TeamRow:
    """One lasting team: its name, captain (None if unset), members longest-standing first, and its tournament entries."""

    name: str
    captain: ReferenceLink | None
    members: tuple[ReferenceLink, ...]
    entries: tuple[EntryRow, ...] = ()


def _result(entry: TournamentEntry, tournament: Tournament) -> str:
    """Describe how a team's entry in a tournament stands."""
    if tournament.winner_entry_id == entry.id:
        return "Won"
    if tournament.status is TournamentStatus.FINISHED:
        return "Knocked out"
    if tournament.status is TournamentStatus.CANCELLED:
        return "Cancelled"
    if tournament.status is TournamentStatus.RUNNING:
        return "Playing"
    return "Signed up"


def _entries_of(session: Session, team_id: int) -> tuple[EntryRow, ...]:
    """Return the team's alive tournament entries, newest tournament first."""
    entries = list(session.exec(alive(TournamentEntry).where(col(TournamentEntry.team_id) == team_id)))
    if not entries:
        return ()
    tournaments = {
        tournament.id: tournament
        for tournament in session.exec(
            alive(Tournament).where(col(Tournament.id).in_([entry.tournament_id for entry in entries])),
        )
    }
    pairs = [(entry, tournaments[entry.tournament_id]) for entry in entries if entry.tournament_id in tournaments]
    pairs.sort(key=lambda pair: pair[1].created_at, reverse=True)
    return tuple(EntryRow(tournament=tournament.name, result=_result(entry, tournament)) for entry, tournament in pairs)


def _lasting_teams(session: Session, member_id: Snowflake) -> list[tuple[int, Team]]:
    """Return the member's lasting teams with their IDs, by name."""
    return [(team.id, team) for team in teams_of(session, member_id) if team.kind is TeamKind.LASTING and team.id is not None]


def _in_a_team(session: Session, context: ProfileContext) -> bool:
    """Whether the member is in a lasting team."""
    return bool(_lasting_teams(session, context.member_id))


@profile_page(slug="teams", title="Teams", template="profile/teams.html", used=_in_a_team)
def teams(context: ProfileContext) -> dict[str, object]:
    """Return the teams page context: lasting teams by name, each with captain, members and tournament entries."""
    with Session(context.bind) as session:
        drafts = [
            (
                team,
                None if team.captain_id is None else Snowflake(team.captain_id),
                tuple(Snowflake(member.user_id) for member in members_of(session, team)),
                _entries_of(session, team_id),
            )
            for team_id, team in _lasting_teams(session, context.member_id)
        ]
    everyone = dict.fromkeys(
        person for _, captain, members, _ in drafts for person in (() if captain is None else (captain,)) + members
    )
    links = dict(zip(everyone, context.references.users(everyone), strict=True))
    rows = [
        TeamRow(
            name=team.name,
            captain=None if captain is None else links[captain],
            members=tuple(links[member] for member in members),
            entries=entries,
        )
        for team, captain, members, entries in drafts
    ]
    return {"teams": rows, "formed": len(rows)}
