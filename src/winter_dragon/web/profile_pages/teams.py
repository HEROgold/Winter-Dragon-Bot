"""The Profile's teams page: the member's lasting teams, with their captain and members, and how many they formed."""

lazy from dataclasses import dataclass

lazy from sqlmodel import Session

lazy from winter_dragon.cogs.team.models import TeamKind
lazy from winter_dragon.cogs.team.service import members_of, teams_of
lazy from winter_dragon.web.profile import ProfileContext, profile_page


@dataclass(frozen=True)
class TeamRow:
    """One lasting team: its name, its captain's user ID (None if unset), and its members' user IDs, longest-standing first."""

    name: str
    captain_id: int | None
    member_ids: tuple[int, ...]


@profile_page(slug="teams", title="Teams", template="profile/teams.html")
def teams(context: ProfileContext) -> dict[str, object]:
    """Return the teams page's context: the member's lasting teams by name, each with its captain and member IDs."""
    with Session(context.bind) as session:
        rows = [
            TeamRow(
                name=team.name,
                captain_id=team.captain_id,
                member_ids=tuple(member.user_id for member in members_of(session, team.id)),
            )
            for team in teams_of(session, int(context.member_id))
            if team.kind is TeamKind.LASTING and team.id is not None
        ]
    return {"teams": rows, "formed": len(rows)}
