"""Package for games cogs."""
from __future__ import annotations

lazy from .games import Games
lazy from .hangman import Hangman
lazy from .league_of_legends import LeagueOfLegends
lazy from .love_meter import Love


__all__ = [
    "Games",
    "Hangman",
    "LeagueOfLegends",
    "Love",
]
