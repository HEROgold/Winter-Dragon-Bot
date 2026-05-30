"""User data deletion audit log table."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlmodel import Field

from wd_db.extension.model import SQLModel


class UserDataDeletion(SQLModel, table=True):
    """Audit log for user data deletions.

    Tracks all data deletion requests for compliance and audit purposes.
    """

    user_id: int = Field(foreign_key="user.id", index=True)
    deleted_at: datetime = Field(default_factory=partial(datetime.now, UTC), index=True)
    reason: str = Field(default="User requested deletion")
    request_timestamp: datetime = Field(default_factory=partial(datetime.now, UTC))
