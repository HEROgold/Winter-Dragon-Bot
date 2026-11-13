"""What can happen to a team: creating it, keeping a temporary one, listing its members, and members leaving it.

Each function takes an open session and leaves committing to the caller. A refusal raises
:class:`~wd_errors.Refused` saying why, for the member; the caller then drops the session's changes.
"""

lazy from typing import TYPE_CHECKING, override

lazy from sqlmodel import Session, col, select
lazy from wd_db.extension._herogold import Repository
lazy from wd_errors import Refused
lazy from wd_types.clock import utc_now

lazy from winter_dragon.member_hidden import MemberHiddenHook

lazy from .models import Team, TeamKind, TeamMember, TeamOrigin


if TYPE_CHECKING:
    lazy from collections.abc import Generator, Sequence
    lazy from datetime import datetime, timedelta

    lazy from wd_discord.snowflake import Snowflake


def create_team(session: Session, name: str, captain_id: Snowflake) -> Team:
    """Create the lasting team ``name`` with ``captain_id`` as its captain and first member."""
    stripped = name.strip()
    if not stripped:
        msg = "A team needs a name."
        raise Refused(msg)
    team = Repository[Team](session).add(
        Team(name=stripped, kind=TeamKind.LASTING, origin=TeamOrigin.CREATED, captain_id=int(captain_id)),
    )
    session.flush()
    Repository[TeamMember](session).add(TeamMember(team_id=team.id or 0, user_id=int(captain_id), joined_at=utc_now()))
    return team


def create_temporary_teams(session: Session, groups: Sequence[Sequence[Snowflake]], origin: TeamOrigin) -> list[Team]:
    """Store one temporary team per group, named Team 1, Team 2, ..., with no captain; return them in order.

    The teams are stored in one statement, then all their members in another, whatever the number of groups.
    """
    teams = Repository[Team](session).add_all(
        Team(name=f"Team {number}", kind=TeamKind.TEMPORARY, origin=origin) for number in range(1, len(groups) + 1)
    )
    session.flush()
    now = utc_now()
    Repository[TeamMember](session).add_all(
        TeamMember(team_id=team.id or 0, user_id=int(user_id), joined_at=now)
        for team, group in zip(teams, groups, strict=True)
        for user_id in group
    )
    return teams


def require_keepable(session: Session, team: Team, user_id: Snowflake) -> None:
    """Refuse unless ``user_id`` is a member of ``team``, which must be temporary and unended, so they may keep it."""
    if membership(session, team, user_id) is None:
        msg = "Only this team's members can keep it."
        raise Refused(msg)
    if team.ended_at is not None:
        msg = "That team has ended."
        raise Refused(msg)
    if team.kind is TeamKind.LASTING:
        msg = "That team is kept already."
        raise Refused(msg)


def keep(session: Session, team: Team, user_id: Snowflake, name: str) -> None:
    """Make the temporary ``team`` lasting under ``name``, with ``user_id`` as its captain; only its members may."""
    require_keepable(session, team, user_id)
    stripped = name.strip()
    if not stripped:
        msg = "A team needs a name."
        raise Refused(msg)
    team.name = stripped
    team.kind = TeamKind.LASTING
    team.captain_id = int(user_id)
    session.add(team)


def end_expired(session: Session, now: datetime, lifetime: timedelta) -> int:
    """End every alive temporary team, except a solo tournament's, made at or before ``now - lifetime``; return how many.

    One UPDATE, whatever the number of teams.
    """
    cutoff = now - lifetime
    return (
        Repository[Team](session)
        .qs()
        .where(
            col(Team.kind) == TeamKind.TEMPORARY,
            col(Team.ended_at).is_(None),
            col(Team.origin) != TeamOrigin.SOLO_TOURNAMENT,
            col(Team.created_at) <= cutoff,
        )
        .update(ended_at=now)
    )


def end_team(session: Session, team: Team, now: datetime) -> None:
    """End the temporary ``team`` at ``now``; a lasting or already ended team stays as it is."""
    if team.kind is TeamKind.LASTING or team.ended_at is not None:
        return
    team.ended_at = now
    session.add(team)


def members_of(session: Session, team: Team) -> Generator[TeamMember]:
    """Yield the team's members, longest-standing first."""
    query = (
        Repository[TeamMember](session)
        .qs()
        .where(col(TeamMember.team_id) == (team.id or 0))
        .order_by(col(TeamMember.joined_at), col(TeamMember.id))
    )
    yield from query.all()


def teams_of(session: Session, user_id: Snowflake) -> Generator[Team]:
    """Yield the alive, unended teams ``user_id`` is a member of, by name, in one statement."""
    joined = select(col(TeamMember.team_id)).where(col(TeamMember.user_id) == int(user_id), *TeamMember.default_criteria())
    query = (
        Repository[Team](session).qs().where(col(Team.id).in_(joined), col(Team.ended_at).is_(None)).order_by(col(Team.name))
    )
    yield from query.all()


def membership(session: Session, team: Team, user_id: Snowflake) -> TeamMember | None:
    """Return ``user_id``'s alive membership of ``team``, if they're in it."""
    return Repository[TeamMember](session).qs().filter_by(team_id=team.id, user_id=int(user_id)).first()


def leave(session: Session, team: Team, user_id: Snowflake) -> None:
    """Take ``user_id`` out of ``team``.

    A leaving captain hands over to the longest-standing member; the last member leaving disbands the team.
    """
    member = membership(session, team, user_id)
    if member is None:
        msg = "You aren't in that team."
        raise Refused(msg)
    Repository[TeamMember](session).delete(member)
    remaining = list(members_of(session, team))
    if not remaining:
        Repository[Team](session).delete(team)
    elif team.captain_id == int(user_id):
        team.captain_id = remaining[0].user_id
        session.add(team)


def require_captain(team: Team, user_id: Snowflake) -> None:
    """Refuse unless ``user_id`` captains ``team``."""
    if team.captain_id != int(user_id):
        msg = "Only the team's captain can do that."
        raise Refused(msg)


def join(session: Session, team: Team, user_id: Snowflake) -> None:
    """Add ``user_id`` to ``team``, joining now, or bring back the membership they left; refuse when they're in it."""
    if membership(session, team, user_id) is not None:
        msg = "You're in that team already."
        raise Refused(msg)
    Repository[TeamMember](session).upsert([TeamMember(team_id=team.id or 0, user_id=int(user_id), joined_at=utc_now())])


def kick(session: Session, team: Team, captain_id: Snowflake, user_id: Snowflake) -> None:
    """Take ``user_id`` out of ``team`` for its captain; the captain can't kick themselves."""
    require_captain(team, captain_id)
    if user_id == captain_id:
        msg = "Use leave to leave your own team."
        raise Refused(msg)
    member = membership(session, team, user_id)
    if member is None:
        msg = "They aren't in that team."
        raise Refused(msg)
    Repository[TeamMember](session).delete(member)


def hand_over(session: Session, team: Team, captain_id: Snowflake, user_id: Snowflake) -> None:
    """Make the member ``user_id`` captain of ``team``, for its captain."""
    require_captain(team, captain_id)
    if membership(session, team, user_id) is None:
        msg = "They aren't in that team."
        raise Refused(msg)
    team.captain_id = int(user_id)
    session.add(team)


def disband(session: Session, team: Team, captain_id: Snowflake) -> None:
    """Disband ``team`` for its captain: soft-delete it and every membership, in two statements."""
    require_captain(team, captain_id)
    Repository[TeamMember](session).qs().filter_by(team_id=team.id).soft_delete()
    Repository[Team](session).delete(team)


class LeaveHiddenMember(MemberHiddenHook):
    """A member whose data is hidden leaves each of their teams, by the rule ``/team leave`` follows."""

    tables = (Team, TeamMember)

    @classmethod
    @override
    def on_member_hidden(cls, session: Session, member_id: Snowflake) -> None:
        """Take the member ``member_id`` out of every team they're in, handing over captaincies."""
        for team in list(teams_of(session, member_id)):
            leave(session, team, member_id)
