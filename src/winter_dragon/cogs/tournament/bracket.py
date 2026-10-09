"""The arithmetic of a single-elimination bracket, and of splitting players into teams; no database, no Discord."""

from __future__ import annotations

lazy from math import ceil, log2
lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Sequence
    lazy from random import Random


MIN_TEAMS = 2
MAX_VOTE_OPTIONS = 10
"""The most answers a vote offers: two rows of buttons."""
MAX_OPTION_LENGTH = 80
"""Discord's limit on a button label."""


def split_into_teams(user_ids: Sequence[int], team_size: int, rng: Random) -> list[list[int]]:
    """Shuffle ``user_ids`` into teams of ``team_size``; players left over join the first teams, one each.

    Returns no teams when there are too few players for two.
    """
    if team_size < 1 or len(user_ids) < MIN_TEAMS * team_size:
        return []
    shuffled = list(user_ids)
    rng.shuffle(shuffled)
    count = len(shuffled) // team_size
    teams = [shuffled[index * team_size : (index + 1) * team_size] for index in range(count)]
    for index, user_id in enumerate(shuffled[count * team_size :]):
        teams[index].append(user_id)
    return teams


def round_count(teams: int) -> int:
    """Return how many rounds a bracket of ``teams`` teams takes."""
    return max(1, ceil(log2(teams)))


def first_round(team_ids: Sequence[int]) -> list[tuple[int, int | None]]:
    """Pair ``team_ids`` for the first round, in seed order; ``None`` is a bye.

    The bracket is padded to a power of two and seed ``i`` meets seed ``size - 1 - i``, so the byes go to the top
    seeds and two byes never meet.
    """
    size = 2 ** round_count(len(team_ids))
    padded: list[int | None] = [*team_ids, *[None] * (size - len(team_ids))]
    pairs: list[tuple[int, int | None]] = []
    for index in range(size // 2):
        first, second = padded[index], padded[size - 1 - index]
        if first is None:  # can't happen while there are at least two teams; keeps the type exact
            continue
        pairs.append((first, second))
    return pairs


def next_match(round_: int, slot: int) -> tuple[int, int, bool]:
    """Return where the winner of match ``slot`` of round ``round_`` plays next: round, slot, and whether as team A."""
    return round_ + 1, slot // 2, slot % 2 == 0


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
    return MIN_TEAMS <= len(options) <= MAX_VOTE_OPTIONS and all(len(option) <= MAX_OPTION_LENGTH for option in options)


def tally(option_count: int, choices: Iterable[int]) -> list[int]:
    """Count the votes for each of ``option_count`` answers; out-of-range choices are ignored."""
    counts = [0] * option_count
    for choice in choices:
        if 0 <= choice < option_count:
            counts[choice] += 1
    return counts
