"""Splitting members into teams: pure arithmetic, no database, no Discord."""

lazy from typing import TYPE_CHECKING


if TYPE_CHECKING:
    lazy from collections.abc import Sequence
    lazy from random import Random


MIN_TEAMS = 2


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


def split_into(user_ids: Sequence[int], count: int, rng: Random) -> list[list[int]]:
    """Shuffle ``user_ids`` into ``count`` teams whose sizes differ by at most one; none if there are too few players."""
    if count < 1 or len(user_ids) < count:
        return []
    shuffled = list(user_ids)
    rng.shuffle(shuffled)
    teams: list[list[int]] = [[] for _ in range(count)]
    for index, user_id in enumerate(shuffled):
        teams[index % count].append(user_id)
    return teams
