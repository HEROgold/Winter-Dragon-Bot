"""Discord CDN image hashes and formats (https://docs.discord.com/developers/reference#image-formatting)."""
from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic_core import core_schema


if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema


class ImageHash:
    """https://docs.discord.com/developers/reference#image-formatting.

    Wraps a Discord CDN image hash (avatar, banner, icon, splash, ...). Validated by pydantic
    from the raw hash string and serialised back to it.
    """

    base_url = "https://cdn.discordapp.com/"

    def __init__(self, hash_: str) -> None:
        """Store the CDN image ``hash_``."""
        self.hash = hash_

    def __eq__(self, other: object) -> bool:
        """Two hashes are equal when their hash strings match."""
        return isinstance(other, ImageHash) and other.hash == self.hash

    def __hash__(self) -> int:
        """Hash by the underlying hash string so instances are usable in sets/dicts."""
        return hash(self.hash)

    def __str__(self) -> str:
        """Return the raw hash string."""
        return self.hash

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"ImageHash({self.hash!r})"

    @classmethod
    def _validate(cls, value: Any) -> ImageHash:  # noqa: ANN401 - pydantic hands us an untyped input
        """Coerce a raw hash ``str`` into an :class:`ImageHash`."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(value)
        msg = f"Cannot build ImageHash from {type(value).__name__}."
        raise TypeError(msg)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        """Validate from a hash ``str`` and serialise back to it."""
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda image_hash: image_hash.hash,
                return_schema=core_schema.str_schema(),
                when_used="json",
            ),
        )


class ImageFormats(StrEnum):
    """Valid image formats supported by Discord."""

    JPG = ".jpg"
    JPEG = ".jpeg"
    """Could be either .jpg or .jpeg."""
    PNG = ".png"
    WebP = ".webp"
    GIF = ".gif"
    Lottie = ".json"
