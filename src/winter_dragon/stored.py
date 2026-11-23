"""Loading a stored row a command needs, refusing when it's gone."""

from typing import TYPE_CHECKING

lazy from wd_db.extension.lifecycle import alive_by_id
lazy from wd_errors import Refused


if TYPE_CHECKING:
    lazy from sqlmodel import Session
    lazy from wd_db.extension.lifecycle import LifecycleModel


def stored[M: LifecycleModel](session: Session, model: type[M], record_id: int, gone: str) -> M:
    """Return the alive ``model`` stored as ``record_id``; refuse with ``gone`` when there's none."""
    record = alive_by_id(session, model, record_id)
    if record is None:
        raise Refused(gone)
    return record
