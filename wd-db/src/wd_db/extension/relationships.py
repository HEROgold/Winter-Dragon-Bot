"""Read and replace a herogold ``Relationship`` link inside the caller's session, without committing.

A herogold ``Relationship`` keeps its link in a per-model link table. Assigning through the descriptor
(``row.owner = account``) writes that table through herogold's own class-level session and commits at once
(HeroPy#56), so it can't be part of a cog's transaction: a later failure can't roll the link back, and the
link is written to whichever database herogold's session points at. Use :func:`linked` and :func:`link`
instead; they act on the session you pass and leave committing to you.
"""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, cast

lazy from herogold.orm.core.utils import Relationship
lazy from sqlmodel import select

# Imported eagerly, before herogold's models: ``_herogold`` stops herogold writing a ``db_config.ini``.
from wd_db.extension._herogold import BaseModel  # noqa: F401


if TYPE_CHECKING:
    lazy from herogold.orm.core.model import _BaseModel
    lazy from herogold.orm.core.utils import LinkInfo
    lazy from sqlmodel import Session


# TODO(Herogold, HeroPy#56): assign through the descriptor once it takes the caller's session.  # noqa: FIX002


def linked[T: _BaseModel](session: Session, owner: _BaseModel, name: str) -> T | None:
    """Return what ``owner``'s relationship ``name`` links to, or ``None`` when it links nothing."""
    info = _link_info(owner, name)
    query = select(info.target).join(info.table, info.target_join()).where(info.owner_filter(owner))
    return cast("T | None", session.exec(query).first())


def link(session: Session, owner: _BaseModel, name: str, target: _BaseModel | None) -> None:
    """Make ``owner``'s relationship ``name`` link to ``target``, replacing its link; ``None`` removes it.

    ``owner`` must be flushed (it needs its ``id``); an unsaved ``target`` is added and flushed. The caller commits.
    """
    info = _link_info(owner, name)
    session.exec(info.table.delete().where(info.owner_filter(owner)))
    if target is None:
        return
    if target.id is None:
        session.add(target)
        session.flush()
    session.exec(info.table.insert().values(**info.owner_values(owner), **info.target_values(target)))


def _link_info(owner: _BaseModel, name: str) -> LinkInfo[_BaseModel]:
    """Return the link table behind ``owner``'s relationship ``name``."""
    for cls in type(owner).__mro__:
        descriptor = vars(cls).get(name)
        if isinstance(descriptor, Relationship):
            return descriptor._links[type(owner)]  # noqa: SLF001 - herogold has no public accessor
    msg = f"{type(owner).__name__} has no relationship named {name!r}."
    raise AttributeError(msg)
