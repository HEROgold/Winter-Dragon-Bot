from __future__ import annotations

lazy from dataclasses import dataclass, field


@dataclass
class Player:
    name: str
    intended_pick: str


@dataclass
class Teams:
    players: list[Player]


@dataclass
class MatchInformation:
    teams: list[Teams]
    status: MatchStatus
    controller: object = field(default=match_controller, repr=False, compare=False)
