"""The features a member's data belongs to, as the data page groups it; a feature registers its own tables.

Creating a :class:`DataCategory` registers it, so privacy and the dashboard needn't know the features. A table no
feature registers falls under the name of the cog package that defines it, so nothing a member owns goes unlisted.
"""

from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, ClassVar


if TYPE_CHECKING:
    lazy from wd_db.extension.lifecycle import LifecycleModel


COGS_PACKAGE = "winter_dragon.cogs."


@dataclass(frozen=True)
class DataCategory:
    """A feature's name on the data page, and the tables that hold its data; creating one registers it.

    A table registered again (a reloaded extension) moves to the newest category that names it. Tables are matched by
    table name, so a reloaded model class still finds its category.
    """

    name: str
    tables: tuple[type[LifecycleModel], ...]
    _by_table: ClassVar[dict[str, DataCategory]] = {}

    def __post_init__(self) -> None:
        """Register the category under each of its tables' names."""
        for table in self.tables:
            DataCategory._by_table[table.__table__.name] = self

    @staticmethod
    def registered_for(model: type[LifecycleModel]) -> DataCategory | None:
        """Return the category ``model``'s table is registered under; ``None`` if none."""
        return DataCategory._by_table.get(model.__table__.name)

    @staticmethod
    def of(model: type[LifecycleModel]) -> str:
        """Return the name of the category ``model`` is registered under, else its cog package's name in words."""
        category = DataCategory.registered_for(model)
        if category is not None:
            return category.name
        package = model.__module__.removeprefix(COGS_PACKAGE).split(".")[0]
        return package.replace("_", " ").capitalize()
