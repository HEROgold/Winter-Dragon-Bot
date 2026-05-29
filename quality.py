from __future__ import annotations

from random import random


class Quality(int):
    """Represents the quality of an item, with higher values indicating better quality."""

def quality(chance: float) -> Quality:
    """Assign a quality to the given item."""
    quality = Quality(0)
    while random() < chance:  # noqa: S311
        quality = Quality(quality + 1)
    return quality
