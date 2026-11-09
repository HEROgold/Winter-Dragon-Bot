"""The arithmetic of a single-elimination bracket, and of splitting players into teams; no database, no Discord."""

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from math import ceil, log2

lazy from wd_discord.limits import MAX_ACTION_ROW_BUTTONS, MAX_BUTTON_LABEL_LENGTH

lazy from winter_dragon.cogs.team.split import MIN_TEAMS


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Sequence


MAX_VOTE_OPTIONS = 2 * MAX_ACTION_ROW_BUTTONS
"""The most answers a vote offers: two rows of buttons."""
MAX_QUESTION_LENGTH = 200
"""The longest vote question; it fits in the vote embed's title (``MAX_EMBED_TITLE_LENGTH``) with its prefix."""


@dataclass(frozen=True)
class Pairing[T]:
    """Two seeds meeting in a first-round match; ``second`` is ``None`` for a bye."""

    first: T
    second: T | None

    @property
    def bye(self) -> bool:
        """Whether ``first`` goes through without playing."""
        return self.second is None


@dataclass(frozen=True)
class BracketSlot:
    """Where in the bracket a match sits: its round (0 first) and its place in that round, top to bottom."""

    round: int
    slot: int


@dataclass(frozen=True)
class NextMatch:
    """Where a match's winner plays next, and on which side."""

    at: BracketSlot
    as_entry_a: bool


def round_count(teams: int) -> int:
    """Return how many rounds a bracket of ``teams`` teams takes."""
    return max(1, ceil(log2(teams)))


def first_round[T](seeds: Sequence[T]) -> list[Pairing[T]]:
    """Pair ``seeds`` for the first round, in seed order; a ``None`` second seed is a bye.

    The bracket is padded to a power of two and seed ``i`` meets seed ``size - 1 - i``, so the byes go to the top
    seeds and two byes never meet.
    """
    size = 2 ** round_count(len(seeds))
    padded: list[T | None] = [*seeds, *[None] * (size - len(seeds))]
    pairs: list[Pairing[T]] = []
    for index in range(size // 2):
        first, second = padded[index], padded[size - 1 - index]
        if first is None:  # can't happen while there are at least two seeds; keeps the type exact
            continue
        pairs.append(Pairing(first, second))
    return pairs


def next_match(at: BracketSlot) -> NextMatch:
    """Return where the winner of the match at ``at`` plays next: its round, its slot, and whether as entry A."""
    return NextMatch(BracketSlot(at.round + 1, at.slot // 2), at.slot % 2 == 0)


def round_name(round_: int, rounds: int) -> str:
    """Return how players call round ``round_`` of a bracket of ``rounds`` rounds."""
    remaining = rounds - round_
    return {1: "Final", 2: "Semi-finals", 3: "Quarter-finals"}.get(remaining, f"Round {round_ + 1}")


def parse_options(text: str) -> list[str]:
    """Split comma-separated answers, dropping blanks and repeats; check the vote's limits with :func:`valid_options`."""
    seen: dict[str, None] = {}
    for option in text.split(","):
        stripped = option.strip()
        if stripped:
            seen.setdefault(stripped, None)
    return list(seen)


def valid_options(options: Sequence[str]) -> bool:
    """Whether ``options`` can be voted on: 2 to :data:`MAX_VOTE_OPTIONS` answers that fit on a button."""
    return MIN_TEAMS <= len(options) <= MAX_VOTE_OPTIONS and all(len(option) <= MAX_BUTTON_LABEL_LENGTH for option in options)


def tally(option_count: int, choices: Iterable[int]) -> list[int]:
    """Count the votes for each of ``option_count`` answers; out-of-range choices are ignored."""
    counts = [0] * option_count
    for choice in choices:
        if 0 <= choice < option_count:
            counts[choice] += 1
    return counts
