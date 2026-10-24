"""The SQLModel tables a module defines, set aside while the module is executed again by a hot reload."""

lazy import inspect
lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING

lazy from sqlalchemy import Table
lazy from sqlmodel import SQLModel


if TYPE_CHECKING:
    lazy from types import ModuleType


@dataclass
class ModuleTables:
    """The tables of a module's table classes, taken out of ``SQLModel.metadata`` so the module can define them again.

    SQLAlchemy refuses a second table under a name ``SQLModel.metadata`` already holds, so re-executing a module that
    defines ``table=True`` models fails unless its tables are detached first.
    """

    detached: list[Table]
    present: set[str]
    """The metadata's table keys right after detaching; any key added later came from the new module."""

    @classmethod
    def detach(cls, module_name: str, module: ModuleType | None) -> ModuleTables:
        """Remove the tables of the classes ``module`` defines from ``SQLModel.metadata``; ``None`` detaches nothing."""
        metadata = SQLModel.metadata
        tables: dict[str, Table] = {}
        for obj in vars(module).values() if module is not None else ():
            table = getattr(obj, "__table__", None)
            if inspect.isclass(obj) and obj.__module__ == module_name and isinstance(table, Table):
                tables[table.key] = table
        detached = [table for key, table in tables.items() if metadata.tables.get(key) is table]
        for table in detached:
            metadata.remove(table)
        return cls(detached, set(metadata.tables))

    def restore(self) -> None:
        """Drop the tables added since :meth:`detach` and put the detached ones back, as before the reload."""
        metadata = SQLModel.metadata
        for key in set(metadata.tables) - self.present:
            metadata.remove(metadata.tables[key])
        for table in self.detached:
            metadata._add_table(table.name, table.schema, table)  # noqa: SLF001 - MetaData has no public way to re-add a Table
