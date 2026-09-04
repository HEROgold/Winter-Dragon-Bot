"""Package for user cogs."""
from __future__ import annotations

lazy from .car_fuel import Fuel
lazy from .reminder import Reminder


__all__ = [
    "Fuel",
    "Reminder",
]
