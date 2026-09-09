"""Runtime resolution of a gateway dispatch (event name, payload) pair into a typed model.

The typed ``@overload`` signatures for :func:`parse_dispatch` live in the paired
``dispatch.pyi`` - GENERATED, see ``wd-discord/scripts/generate_dispatch_overloads.py`` - not in
this file. A stub file shadows its ``.py`` module entirely for type checkers, so this module's
own annotations on :func:`parse_dispatch` are irrelevant to callers; only the behavior matters
here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .events import EventName, RawEvent


if TYPE_CHECKING:
    from collections.abc import Mapping

    from wd_discord.models import DiscordModel


def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel:
    """Parse a dispatch (``t``, ``d``) pair into its typed model, or a RawEvent fallback.

    READY is intentionally not handled here - it's parsed once via
    wd_discord.gateway.connection.parse_ready before the continuous receive loop starts, and
    never appears again on the same connection.
    """
    try:
        event = EventName(name)
    except ValueError:
        return RawEvent(name=name, data=data)
    if event.model is None:
        return RawEvent(name=name, data=data)
    return event.model.model_validate(data)
