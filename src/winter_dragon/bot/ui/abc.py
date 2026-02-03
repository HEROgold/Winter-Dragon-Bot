from collections.abc import Callable
from types import CoroutineType
from typing import Protocol

from discord import Interaction


type InteractEvent[T] = Callable[[Interaction], CoroutineType[T, T, None]]

class InteractAble[T = None](Protocol):
    """Protocol for objects that can handle interaction events."""

    on_interact: InteractEvent[T]

async def default_interact(interaction: Interaction) -> None:
    """no-op interaction handler."""
