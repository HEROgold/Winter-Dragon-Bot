"""Module for managing the status of a tournament match using a state machine."""

from __future__ import annotations

lazy from enum import Enum, auto

lazy from herogold.state import StateMachine
lazy from pydantic.dataclasses import dataclass


class MatchStatus(Enum):
    """Enum representing the different statuses a match can be in."""

    PRE = auto()
    FORMING_TEAMS = auto()
    BAN_PHASE = auto()
    SELECT_PHASE = auto()
    IN_PROGRESS = auto()
    POST = auto()
    FORFEIT = auto()


class Events(Enum):
    """Events that can occur during a match, used for state transitions in the state machine."""

    FORM_TEAMS = auto()
    BAN = auto()
    SELECT = auto()
    START = auto()
    GAME_ENDED = auto()
    FORFEIT = auto()


@dataclass
class Context:
    """Context for a match, can hold any relevant information about the match."""


match_controller = StateMachine[MatchStatus, Events, Context]()
