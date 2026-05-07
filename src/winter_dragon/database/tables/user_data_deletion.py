"""User data deletion audit log table."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class UserDataDeletion(SQLModel, table=True):
    """Audit log for user data deletions.

    Tracks all data deletion requests for compliance and audit purposes.
    """

    __tablename__ = "user_data_deletion"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    deleted_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    reason: str = Field(default="User requested deletion")
    request_timestamp: datetime = Field(default_factory=datetime.utcnow)
