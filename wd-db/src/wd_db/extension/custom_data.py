"""Read and replace a herogold model's custom data inside the caller's session.

Every herogold model links to at most one ``CustomData`` row (a JSONB blob) through its own
``<table>_custom_data`` link table. herogold's ``Relationship`` writes that link through its own
class-level session and commits on every assignment, so it can't take part in a caller's
transaction (HeroPy#56). These helpers write the same rows with the caller's session instead and
leave committing to the caller.
"""

lazy from typing import TYPE_CHECKING, Any

lazy from herogold.orm.core.model import CustomData, _BaseModel
lazy from sqlmodel import col, delete, select

# Imported eagerly, before herogold's models: ``_herogold`` stops herogold writing a ``db_config.ini``.
from wd_db.extension._herogold import BaseModel  # noqa: F401


if TYPE_CHECKING:
    lazy from herogold.orm.core.utils import LinkInfo
    lazy from sqlmodel import Session


__all__ = ["CustomData", "get_custom_data", "set_custom_data"]

# TODO(Herogold, HeroPy#56): use ``row.custom_data`` once herogold's Relationship takes the caller's session.  # noqa: FIX002


def get_custom_data(session: Session, row: _BaseModel) -> dict[str, Any]:
    """Return ``row``'s custom data, or an empty dict when it has none."""
    link = _link(row)
    stored = session.exec(select(CustomData).join(link.table, link.target_join()).where(link.owner_filter(row))).first()
    return {} if stored is None else stored.data


def set_custom_data(session: Session, row: _BaseModel, data: dict[str, Any]) -> None:
    """Replace ``row``'s custom data with ``data``; an empty ``data`` removes it. ``row`` must be flushed; caller commits."""
    link = _link(row)
    (target_column,) = link.target_cols
    old_id = session.exec(select(link.table.c[target_column]).where(link.owner_filter(row))).first()
    session.exec(link.table.delete().where(link.owner_filter(row)))
    if old_id is not None:
        session.exec(delete(CustomData).where(col(CustomData.id) == old_id))
    if not data:
        return
    stored = CustomData(data=data)
    session.add(stored)
    session.flush()
    session.exec(link.table.insert().values(**link.owner_values(row), **link.target_values(stored)))


def _link(row: _BaseModel) -> LinkInfo[CustomData]:
    """Return the link table joining ``row``'s model to ``CustomData``."""
    return _BaseModel.__dict__["custom_data"]._links[type(row)]  # noqa: SLF001 - herogold has no public accessor
