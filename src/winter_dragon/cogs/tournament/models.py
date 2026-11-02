"""The tournament tables: a tournament, its teams and players, its bracket's matches, their drafts and votes."""

from enum import StrEnum
lazy from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.lifecycle import LifecycleModel, Ownership, Through


class TeamMode(StrEnum):
    """How a tournament's teams are formed."""

    SOLO = "solo"
    """Players sign up alone; starting the tournament shuffles them into teams."""
    CAPTAINS = "captains"
    """Captains register a team and add its players."""


class TournamentStatus(StrEnum):
    """Where a tournament is in its life."""

    SIGNUP = "signup"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class MatchPhase(StrEnum):
    """Where a match is: waiting for its teams, through the draft, live, and decided."""

    WAITING = "waiting"
    """An earlier round hasn't decided one of its teams yet."""
    READY = "ready"
    BAN = "ban"
    PICK = "pick"
    LIVE = "live"
    FINISHED = "finished"
    FORFEIT = "forfeit"
    """Decided because a team forfeited."""

    @property
    def decided(self) -> bool:
        """Whether the match has a winner."""
        return self in {MatchPhase.FINISHED, MatchPhase.FORFEIT}

    @property
    def next(self) -> MatchPhase | None:
        """The phase an organiser advances the match to; ``None`` when the next step is reporting a winner."""
        return {MatchPhase.READY: MatchPhase.BAN, MatchPhase.BAN: MatchPhase.PICK, MatchPhase.PICK: MatchPhase.LIVE}.get(self)


class DraftKind(StrEnum):
    """Whether a team bans something from the match, or picks it."""

    BAN = "ban"
    PICK = "pick"


ACTIVE = (TournamentStatus.SIGNUP, TournamentStatus.RUNNING)
"""The statuses of a tournament that isn't over; a guild has at most one."""


class Tournament(LifecycleModel, table=True):
    """A guild's tournament, run in one channel by its organiser; the guild owns it and everything in it."""

    ownership: ClassVar[Ownership] = Ownership(guild="guild_id")

    guild_id: int = Field(sa_type=BigInteger, index=True)
    channel_id: int = Field(sa_type=BigInteger)
    organiser_id: int = Field(sa_type=BigInteger)
    name: str
    mode: TeamMode
    team_size: int
    status: TournamentStatus = TournamentStatus.SIGNUP
    winner_team_id: int | None = None


class TournamentTeam(LifecycleModel, table=True):
    """A team in a tournament; its captain bans and picks for it."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("tournament_id", Tournament))

    tournament_id: int = Field(index=True)
    name: str
    captain_id: int = Field(sa_type=BigInteger)


class TournamentPlayer(LifecycleModel, table=True):
    """A player signed up for a tournament, and the team they play in once they have one."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id", through=Through("tournament_id", Tournament))
    natural_key: ClassVar[tuple[str, ...]] = ("tournament_id", "user_id")

    tournament_id: int = Field(index=True)
    user_id: int = Field(sa_type=BigInteger)
    team_id: int | None = None


class TournamentMatch(LifecycleModel, table=True):
    """One match of a tournament's single-elimination bracket; round 0 is the first."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("tournament_id", Tournament))

    tournament_id: int = Field(index=True)
    round: int
    slot: int
    """The match's place in its round, top to bottom; it feeds slot ``slot // 2`` of the next round."""
    team_a_id: int | None = None
    team_b_id: int | None = None
    phase: MatchPhase = MatchPhase.WAITING
    winner_id: int | None = None


class DraftChoice(LifecycleModel, table=True):
    """Something a team banned from, or picked for, a match."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("match_id", TournamentMatch))

    match_id: int = Field(index=True)
    team_id: int
    kind: DraftKind
    value: str


class MatchVote(LifecycleModel, table=True):
    """A question the players of a match vote on, like which map to play."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("match_id", TournamentMatch))

    match_id: int = Field(index=True)
    question: str
    options: str
    """The answers to choose from, one per line."""
    open: bool = True


class MatchBallot(LifecycleModel, table=True):
    """One player's answer to a vote; voting again changes it."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id", through=Through("vote_id", MatchVote))
    natural_key: ClassVar[tuple[str, ...]] = ("vote_id", "user_id")

    vote_id: int = Field(index=True)
    user_id: int = Field(sa_type=BigInteger)
    choice: int
    """The index of the chosen answer."""


TOURNAMENT_TABLES = (Tournament, TournamentTeam, TournamentPlayer, TournamentMatch, DraftChoice, MatchVote, MatchBallot)
