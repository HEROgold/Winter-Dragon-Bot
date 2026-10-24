"""Discord's RGB color, an integer on the wire."""

lazy from typing import TYPE_CHECKING, Any, Self

lazy from pydantic_core import core_schema


if TYPE_CHECKING:
    lazy from pydantic import GetCoreSchemaHandler
    lazy from pydantic_core import CoreSchema


MAX_COLOR = 0xFFFFFF
"""The largest color: Discord's colors are 24-bit RGB integers (https://docs.discord.com/developers/resources/message#embed-object-embed-structure)."""


class Color(int):
    """An RGB color, ``0x000000`` to ``0xFFFFFF``; still an ``int``, so it goes on the wire unchanged."""

    __slots__ = ()

    def __new__(cls, value: int) -> Self:
        """Reject values outside 24-bit RGB."""
        if not 0 <= value <= MAX_COLOR:
            msg = f"A color is between 0 and {MAX_COLOR:#08x}, got {value}."
            raise ValueError(msg)
        return super().__new__(cls, value)

    @classmethod
    def from_hex(cls, text: str) -> Color:
        """Parse ``"#00ff00"``, ``"00ff00"`` or ``"0x00ff00"``."""
        return cls(int(text.removeprefix("#").removeprefix("0x"), 16))

    def __str__(self) -> str:
        """Return the ``#rrggbb`` form."""
        return f"#{int(self):06x}"

    def __repr__(self) -> str:
        return f"Color({self})"

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> CoreSchema:
        """Validate from an ``int`` in range and serialise back to a plain ``int``."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.int_schema(ge=0, le=MAX_COLOR),
            serialization=core_schema.plain_serializer_function_ser_schema(int, return_schema=core_schema.int_schema()),
        )
