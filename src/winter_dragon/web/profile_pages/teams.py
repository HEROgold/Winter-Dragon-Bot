"""The Profile's teams page: the member's lasting teams, with their captain, members, and the tournaments each one entered."""

lazy from dataclasses import dataclass

lazy from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive

lazy from winter_dragon.cogs.team.models import TeamKind
lazy from winter_dragon.cogs.team.service import members_of, teams_of
lazy from winter_dragon.cogs.tournament.models import Tournament, TournamentEntry, TournamentStatus
lazy from winter_dragon.web.profile import ProfileContext, profile_page


@dataclass(frozen=True)
class EntryRow:
    """One tournament a team entered, and how it went for the team."""

    tournament: str
    result: str


@dataclass(frozen=True)
class TeamRow:
    """One lasting team: its name, captain ID (None if unset), member IDs longest-standing first, and its tournament entries."""

    name: str
    captain_id: int | None
    member_ids: tuple[int, ...]
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


@profile_page(slug="teams", title="Teams", template="profile/teams.html")
def teams(context: ProfileContext) -> dict[str, object]:
    """Return the teams page context: lasting teams by name, each with captain, member IDs and tournament entries."""
    with Session(context.bind) as session:
        rows = [
            TeamRow(
                name=team.name,
                captain_id=team.captain_id,
                member_ids=tuple(member.user_id for member in members_of(session, team.id)),
                entries=_entries_of(session, team.id),
            )
            for team in teams_of(session, int(context.member_id))
            if team.kind is TeamKind.LASTING and team.id is not None
        ]
    return {"teams": rows, "formed": len(rows)}
