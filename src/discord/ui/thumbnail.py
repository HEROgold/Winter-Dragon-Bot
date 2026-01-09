"""The MIT License (MIT).

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypeVar

from discord.components import UnfurledMediaItem
from discord.enums import ComponentType
from discord.file import File
from discord.utils import MISSING

from .item import Item


if TYPE_CHECKING:
    from typing import Self

    from discord.components import ThumbnailComponent

    from .view import LayoutView

V = TypeVar("V", bound="LayoutView", covariant=True)

__all__ = ("Thumbnail",)


class Thumbnail(Item[V]):
    r"""Represents a UI Thumbnail. This currently can only be used as a :class:`Section`\'s accessory.

    .. versionadded:: 2.6

    Parameters
    ----------
    media: Union[:class:`str`, :class:`discord.File`, :class:`discord.UnfurledMediaItem`]
        The media of the thumbnail. This can be a URL or a reference
        to an attachment that matches the ``attachment://filename.extension``
        structure.
    description: Optional[:class:`str`]
        The description of this thumbnail. Up to 256 characters. Defaults to ``None``.
    spoiler: :class:`bool`
        Whether to flag this thumbnail as a spoiler. Defaults to ``False``.
    id: Optional[:class:`int`]
        The ID of this component. This must be unique across the view.

    """

    __slots__ = (
        "_media",
        "description",
        "spoiler",
    )
    __item_repr_attributes__ = (
        "media",
        "description",
        "spoiler",
        "row",
        "id",
    )

    def __init__(
        self,
        media: str | File | UnfurledMediaItem,
        *,
        description: str | None = MISSING,
        spoiler: bool = MISSING,
        id: int | None = None,
    ) -> None:
        super().__init__()

        if isinstance(media, File):
            description = description if description is not MISSING else media.description
            spoiler = spoiler if spoiler is not MISSING else media.spoiler
            media = media.uri

        self._media: UnfurledMediaItem = UnfurledMediaItem(media) if isinstance(media, str) else media
        self.description: str | None = None if description is MISSING else description
        self.spoiler: bool = bool(spoiler)

        self.id = id

    @property
    def width(self) -> int:
        return 5

    @property
    def media(self) -> UnfurledMediaItem:
        """:class:`discord.UnfurledMediaItem`: This thumbnail unfurled media data."""
        return self._media

    @media.setter
    def media(self, value: str | File | UnfurledMediaItem) -> None:
        if isinstance(value, str):
            self._media = UnfurledMediaItem(value)
        elif isinstance(value, UnfurledMediaItem):
            self._media = value
        elif isinstance(value, File):
            self._media = UnfurledMediaItem(value.uri)
        else:
            msg = f"expected a str or UnfurledMediaItem, not {value.__class__.__name__!r}"
            raise TypeError(msg)

    @property
    def type(self) -> Literal[ComponentType.thumbnail]:
        return ComponentType.thumbnail

    def _is_v2(self) -> bool:
        return True

    def to_component_dict(self) -> dict[str, Any]:
        base = {
            "type": self.type.value,
            "spoiler": self.spoiler,
            "media": self.media.to_dict(),
            "description": self.description,
        }
        if self.id is not None:
            base["id"] = self.id
        return base

    @classmethod
    def from_component(cls, component: ThumbnailComponent) -> Self:
        return cls(
            media=component.media.url,
            description=component.description,
            spoiler=component.spoiler,
            id=component.id,
        )
