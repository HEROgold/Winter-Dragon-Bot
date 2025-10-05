"""A patched version of CogMeta to fix issues.

- Add auto_load keyword argument to cogs.
"""

from typing import TYPE_CHECKING, Any, Unpack

from discord.ext.commands.cog import CogMeta as OriginalCogMeta


if TYPE_CHECKING:
    from discord.ext.commands.cog import _CogKwargs as Original_CogKwargs  # pyright: ignore[reportPrivateUsage]

    class _CogKwargs(Original_CogKwargs):
        auto_load: bool = False


class CogMeta(OriginalCogMeta):
    """A patched version of CogMeta to fix issues."""

    def __new__(cls, *args: Any, **kwargs: Unpack[_CogKwargs]) -> OriginalCogMeta:  # noqa: ANN401
        """Create a new instance of the metaclass."""
        return super().__new__(*args, **kwargs)
