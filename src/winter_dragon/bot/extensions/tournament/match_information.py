from __future__ import annotations

from dataclasses import dataclass

from winter_dragon.bot.extensions.tournament.status import MatchStatus, match_controller


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
    controller = match_controller
