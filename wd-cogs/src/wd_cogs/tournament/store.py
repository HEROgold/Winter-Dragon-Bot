"""Shared tournament registry for Discord and API surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from .match_information import MatchInformation, Teams
from .status import MatchStatus


@dataclass(slots=True)
class TournamentSnapshot:
    """Serializable tournament view for the API layer."""

    guild_id: int
    status: MatchStatus
    teams: list[Teams]


class TournamentRegistry:
    """In-memory registry for tournament match state."""

    def __init__(self) -> None:
        self._matches: dict[int, MatchInformation] = {}

    def get_match(self, guild_id: int) -> MatchInformation:
        match = self._matches.get(guild_id)
        if match is None:
            match = MatchInformation(teams=[Teams(players=[]), Teams(players=[])], status=MatchStatus.PRE)
            self._matches[guild_id] = match
        return match

    def snapshot(self, guild_id: int) -> TournamentSnapshot:
        match = self.get_match(guild_id)
        return TournamentSnapshot(guild_id=guild_id, status=match.status, teams=match.teams)


registry = TournamentRegistry()
