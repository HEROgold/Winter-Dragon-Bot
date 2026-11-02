"""The arithmetic of a single-elimination bracket, and of splitting players into teams; no database, no Discord."""

lazy from math import ceil, log2
lazy from typing import TYPE_CHECKING

lazy from wd_discord.limits import MAX_ACTION_ROW_BUTTONS, MAX_BUTTON_LABEL_LENGTH

lazy from winter_dragon.cogs.team.split import MIN_TEAMS


if TYPE_CHECKING:
    lazy from collections.abc import Iterable, Sequence


MAX_VOTE_OPTIONS = 2 * MAX_ACTION_ROW_BUTTONS
"""The most answers a vote offers: two rows of buttons."""
MAX_QUESTION_LENGTH = 200
"""The longest vote question; it fits in the vote embed's title (``MAX_EMBED_TITLE_LENGTH``) with its prefix."""


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
    return MIN_TEAMS <= len(options) <= MAX_VOTE_OPTIONS and all(len(option) <= MAX_BUTTON_LABEL_LENGTH for option in options)


def tally(option_count: int, choices: Iterable[int]) -> list[int]:
    """Count the votes for each of ``option_count`` answers; out-of-range choices are ignored."""
    counts = [0] * option_count
    for choice in choices:
        if 0 <= choice < option_count:
            counts[choice] += 1
    return counts
