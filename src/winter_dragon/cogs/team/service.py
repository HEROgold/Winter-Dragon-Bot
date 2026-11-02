"""What can happen to a lasting team: creating it, listing its members, and members leaving it.

Each function takes an open session and leaves committing to the caller. A refusal raises
:class:`~wd_errors.Refused` saying why, for the member; the caller then drops the session's changes.
"""

lazy from typing import TYPE_CHECKING

from sqlmodel import Session, col
lazy from wd_db.extension.lifecycle import alive, create_or_restore, soft_delete
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from .models import Team, TeamKind, TeamMember, TeamOrigin


if TYPE_CHECKING:
    lazy from collections.abc import Generator


def create_team(session: Session, name: str, captain_id: int) -> Team:
    """Create the lasting team ``name`` with ``captain_id`` as its captain and first member."""
    stripped = name.strip()
    if not stripped:
        msg = "A team needs a name."
        raise Refused(msg)
    team = Team(name=stripped, kind=TeamKind.LASTING, origin=TeamOrigin.CREATED, captain_id=captain_id)
    session.add(team)
    session.flush()
    create_or_restore(session, TeamMember(team_id=team.id or 0, user_id=captain_id, joined_at=utc_now()))
    return team


def members_of(session: Session, team_id: int) -> Generator[TeamMember]:
    """Yield the team's members, longest-standing first."""
    query = alive(TeamMember).where(TeamMember.team_id == team_id).order_by(col(TeamMember.joined_at), col(TeamMember.id))
    yield from session.exec(query)


def teams_of(session: Session, user_id: int) -> Generator[Team]:
    """Yield the alive, unended teams ``user_id`` is a member of, by name."""
    team_ids = [member.team_id for member in session.exec(alive(TeamMember).where(TeamMember.user_id == user_id))]
    query = alive(Team).where(col(Team.id).in_(team_ids), col(Team.ended_at).is_(None)).order_by(col(Team.name))
    yield from session.exec(query)


def membership(session: Session, team: Team, user_id: int) -> TeamMember | None:
    """Return ``user_id``'s alive membership of ``team``, if they're in it."""
    return session.exec(alive(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user_id)).first()


def leave(session: Session, team: Team, user_id: int) -> None:
    """Take ``user_id`` out of ``team``.

    A leaving captain hands over to the longest-standing member; the last member leaving disbands the team.
    """
    member = membership(session, team, user_id)
    if member is None:
        msg = "You aren't in that team."
        raise Refused(msg)
    soft_delete(session, member)
    remaining = list(members_of(session, team.id or 0))
    if not remaining:
        soft_delete(session, team)
    elif team.captain_id == user_id:
        team.captain_id = remaining[0].user_id
        session.add(team)
