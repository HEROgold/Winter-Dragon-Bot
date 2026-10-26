"""The Incremental game catalogue: the currencies and generators the bot's developers define in ``catalogue.toml``.

The file is parsed into frozen pydantic values. An invalid file raises :class:`CatalogueError`, which the cog lets
stop startup. Saves refer to entries by :class:`CurrencyKey` and :class:`GeneratorKey`, never by a database id.
"""

from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import tomllib
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, ValidationError, model_validator
from pydantic_core import core_schema


if TYPE_CHECKING:
    import collections.abc

    from pydantic import GetCoreSchemaHandler


CATALOGUE_PATH = Path(__file__).with_name("catalogue.toml")
"""Where the catalogue lives in the repo."""
MAX_GENERATORS = 24
"""One Refresh button plus a Buy button per generator must fit Discord's 25 buttons on a message."""


class CatalogueError(Exception):
    """The catalogue file is missing, isn't TOML, or doesn't match the schema; the message says what is wrong."""


class _Key(str):
    """A stable string key as pydantic reads it from the catalogue."""

    __slots__ = ()

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: type[Any], _handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Validate a non-empty string, then wrap it as ``cls``."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(min_length=1, strict=True),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


class CurrencyKey(_Key):
    """The stable key of a :class:`Currency`."""

    __slots__ = ()


class GeneratorKey(_Key):
    """The stable key of a :class:`Generator`."""

    __slots__ = ()


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Currency(_Frozen):
    """Something a member collects and spends."""

    key: CurrencyKey
    name: str = Field(min_length=1)
    emoji: str = ""
    starting_amount: float = Field(default=0, ge=0)
    """What a new save starts with."""

    @property
    def label(self) -> str:
        """The name with its emoji, when it has one."""
        return f"{self.emoji} {self.name}".strip()


class Quantity(_Frozen):
    """An amount of one currency."""

    currency: CurrencyKey
    amount: PositiveFloat


class Generator(_Frozen):
    """Something a member buys that makes currencies every second."""

    key: GeneratorKey
    name: str = Field(min_length=1)
    description: str = ""
    price: tuple[Quantity, ...] = Field(min_length=1)
    """The cost of the first one."""
    price_growth: float = Field(default=1.0, ge=1.0)
    """The price is multiplied by this for each one already owned."""
    produces: tuple[Quantity, ...] = Field(min_length=1)
    """What one owned generator makes per second."""

    def price_for(self, owned: int) -> collections.abc.Generator[Quantity]:
        """Yield what the next purchase costs when ``owned`` are already owned."""
        factor = self.price_growth**owned
        for cost in self.price:
            yield Quantity(currency=cost.currency, amount=cost.amount * factor)


class Catalogue(_Frozen):
    """Every currency and generator of the game."""

    currencies: tuple[Currency, ...] = Field(min_length=1)
    generators: tuple[Generator, ...] = Field(max_length=MAX_GENERATORS)

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        """Reject duplicate keys and quantities of currencies that don't exist."""
        currency_keys = [currency.key for currency in self.currencies]
        if len(set(currency_keys)) != len(currency_keys):
            msg = "currency keys must be unique"
            raise ValueError(msg)
        generator_keys = [generator.key for generator in self.generators]
        if len(set(generator_keys)) != len(generator_keys):
            msg = "generator keys must be unique"
            raise ValueError(msg)
        for generator in self.generators:
            for quantity in (*generator.price, *generator.produces):
                if quantity.currency not in currency_keys:
                    msg = f"generator {generator.key!r} uses the unknown currency {quantity.currency!r}"
                    raise ValueError(msg)
        return self

    def currency(self, key: str) -> Currency | None:
        """Return the currency with ``key``, or ``None`` when the catalogue has none."""
        return next((currency for currency in self.currencies if currency.key == key), None)

    def generator(self, key: str) -> Generator | None:
        """Return the generator with ``key``, or ``None`` when the catalogue has none."""
        return next((generator for generator in self.generators if generator.key == key), None)


def load_catalogue(path: Path = CATALOGUE_PATH) -> Catalogue:
    """Parse the catalogue at ``path``.

    Raises:
        CatalogueError: the file can't be read, isn't TOML, or doesn't match the schema.

    """
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        msg = f"Incremental catalogue {path} can't be read: {error}"
        raise CatalogueError(msg) from error
    try:
        return Catalogue.model_validate(raw)
    except ValidationError as error:
        msg = f"Incremental catalogue {path} is invalid:\n{error}"
        raise CatalogueError(msg) from error


@cache
def catalogue() -> Catalogue:
    """Return the catalogue of the repo, loaded on first use."""
    return load_catalogue()
