"""The tournament tables: a tournament, its teams and players, its bracket's matches, their drafts and votes."""

from datetime import datetime
lazy from enum import StrEnum
lazy from typing import ClassVar

from sqlalchemy import BigInteger
from sqlmodel import Field
from wd_db.extension.columns import AwareDateTime
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


class MatchEventKind(StrEnum):
    """What happened in a match."""

    PHASE = "phase"
    DRAFT = "draft"
    VOTE_OPENED = "vote opened"
    VOTE_CLOSED = "vote closed"
    WINNER = "winner"
    FORFEIT = "forfeit"
    CLASH_DROPPED = "clash dropped"


ACTIVE = (TournamentStatus.SIGNUP, TournamentStatus.RUNNING)
"""The statuses of a tournament that isn't over."""


class Tournament(LifecycleModel, table=True):
    """A guild's tournament, shown in any channels it is posted to; the guild owns it and everything in it."""

    ownership: ClassVar[Ownership] = Ownership(guild="guild_id")

    guild_id: int = Field(sa_type=BigInteger, index=True)
    organiser_id: int = Field(sa_type=BigInteger)
    name: str
    mode: TeamMode
    team_size: int
    status: TournamentStatus = TournamentStatus.SIGNUP
    winner_entry_id: int | None = None


class TournamentPost(LifecycleModel, table=True):
    """A message showing a tournament in one channel of its guild; the bot edits it whenever the tournament changes."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("tournament_id", Tournament))

    tournament_id: int = Field(index=True)
    channel_id: int = Field(sa_type=BigInteger)
    message_id: int = Field(sa_type=BigInteger)


class TournamentEntry(LifecycleModel, table=True):
    """A team's place in one tournament; its team's captain bans and picks for it."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("tournament_id", Tournament))

    tournament_id: int = Field(index=True)
    team_id: int = Field(index=True)
    name: str


class TournamentSignup(LifecycleModel, table=True):
    """A member signed up alone for a solo tournament, before its teams are drawn."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id", through=Through("tournament_id", Tournament))
    natural_key: ClassVar[tuple[str, ...]] = ("tournament_id", "user_id")

    tournament_id: int = Field(index=True)
    user_id: int = Field(sa_type=BigInteger)


class EntryPlayer(LifecycleModel, table=True):
    """A member playing for a tournament entry; a member may play for several entries of one tournament."""

    ownership: ClassVar[Ownership] = Ownership(member="user_id", through=Through("entry_id", TournamentEntry))
    natural_key: ClassVar[tuple[str, ...]] = ("entry_id", "user_id")

    entry_id: int = Field(index=True)
    user_id: int = Field(sa_type=BigInteger)


class TournamentMatch(LifecycleModel, table=True):
    """One match of a tournament's single-elimination bracket; round 0 is the first."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("tournament_id", Tournament))

    tournament_id: int = Field(index=True)
    round: int
    slot: int
    """The match's place in its round, top to bottom; it feeds slot ``slot // 2`` of the next round."""
    entry_a_id: int | None = None
    entry_b_id: int | None = None
    phase: MatchPhase = MatchPhase.WAITING
    winner_id: int | None = None
    started_at: datetime | None = Field(default=None, sa_type=AwareDateTime)
    """When the match went live."""
    decided_at: datetime | None = Field(default=None, sa_type=AwareDateTime)
    """When the match got its winner."""
    decided_by: int | None = Field(default=None, sa_type=BigInteger)
    """The member who reported the winner; ``None`` for a bye, which no one reports."""
    anonymised: ClassVar[tuple[str, ...]] = ("decided_by",)


class MatchLineup(LifecycleModel, table=True):
    """A member playing for an entry in one match; a decided match's lineup is what was played."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("match_id", TournamentMatch))
    anonymised: ClassVar[tuple[str, ...]] = ("user_id",)

    match_id: int = Field(index=True)
    entry_id: int = Field(index=True)
    user_id: int = Field(sa_type=BigInteger)


class MatchEvent(LifecycleModel, table=True):
    """Something someone did in a match, and when."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("match_id", TournamentMatch))
    anonymised: ClassVar[tuple[str, ...]] = ("actor_id",)

    match_id: int = Field(index=True)
    kind: MatchEventKind
    actor_id: int = Field(sa_type=BigInteger)
    at: datetime = Field(sa_type=AwareDateTime)
    detail: str = ""


class LineupChange(LifecycleModel, table=True):
    """A member put in or taken out of an entry's lineup, by whom, when, and why."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("entry_id", TournamentEntry))
    anonymised: ClassVar[tuple[str, ...]] = ("user_id", "changed_by")

    entry_id: int = Field(index=True)
    match_id: int | None = None
    """The match whose lineup changed; ``None`` when only the entry's current players did."""
    user_id: int = Field(sa_type=BigInteger)
    playing: bool
    changed_by: int = Field(sa_type=BigInteger)
    changed_at: datetime = Field(sa_type=AwareDateTime)
    reason: str | None = None


class DraftChoice(LifecycleModel, table=True):
    """Something a team banned from, or picked for, a match."""

    ownership: ClassVar[Ownership] = Ownership(through=Through("match_id", TournamentMatch))

    match_id: int = Field(index=True)
    entry_id: int
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


TOURNAMENT_TABLES = (
    Tournament,
    TournamentPost,
    TournamentEntry,
    TournamentSignup,
    EntryPlayer,
    TournamentMatch,
    MatchLineup,
    LineupChange,
    DraftChoice,
    MatchEvent,
    MatchVote,
    MatchBallot,
)
