"""Package for games cogs."""
from __future__ import annotations

from .games import Games
from .hangman import Hangman
from .league_of_legends import LeagueOfLegends
from .love_meter import Love


__all__ = [
    "Games",
    "Hangman",
    "LeagueOfLegends",
    "Love",
]
