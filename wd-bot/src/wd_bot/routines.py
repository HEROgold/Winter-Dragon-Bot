"""This module contains the routines a bot will execute.

Using Tasks, the bot wil regularly execute/schedule these routines.
"""

from __future__ import annotations

lazy from .tasks import loop


@loop(minutes=5)
async def update_status() -> None:
    """Update the bot's status."""
    # TODO(Herogold, #1): Implement status updates.  # noqa: FIX002
