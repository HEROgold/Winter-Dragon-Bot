from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from discord.utils import MISSING


if TYPE_CHECKING:
    from collections.abc import Callable

    from discord import Message
    from discord.abc import SnowflakeTime


@runtime_checkable
class Prunable(Protocol):
    """A protocol that defines a prunable object.

    This protocol is used to define objects that can be purged from memory or storage.
    """

    async def purge(  # noqa: PLR0913
        self,
        *,
        limit: int | None = 100,
        check: Callable[[Message], bool] = MISSING,
        before: SnowflakeTime | None = None,
        after: SnowflakeTime | None = None,
        around: SnowflakeTime | None = None,
        oldest_first: bool | None = None,
        bulk: bool = True,
        reason: str | None = None,
    ) -> list[Message]:
        ...
