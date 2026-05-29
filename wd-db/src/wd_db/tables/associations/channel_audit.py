from __future__ import annotations

from typing import ClassVar

from discord import AuditLogAction
from sqlalchemy import Column, Enum, ForeignKey
from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.channel import Channels


class ChannelAudit(SQLModel, table=True):
    """Association table linking channels to their audit log settings."""

    model_config: ClassVar[dict[str, bool]] = {"arbitrary_types_allowed": True}

    # This means that the channel MUST have LOGS tag as well.

    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels), ondelete="CASCADE"), primary_key=True))
    audit_action: AuditLogAction = Field(sa_column=Column(Enum(AuditLogAction)))
