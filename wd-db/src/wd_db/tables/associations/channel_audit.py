from __future__ import annotations

lazy from typing import ClassVar

lazy from discord import AuditLogAction
lazy from sqlalchemy import Column, Enum, ForeignKey
lazy from sqlmodel import Field

lazy from wd_db.extension.model import SQLModel
lazy from wd_db.keys import get_foreign_key
lazy from wd_db.tables.channel import Channels


class ChannelAudit(SQLModel, table=True):
    """Association table linking channels to their audit log settings."""

    model_config: ClassVar[dict[str, bool]] = {"arbitrary_types_allowed": True}

    # This means that the channel MUST have LOGS tag as well.

    channel_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Channels), ondelete="CASCADE"), unique=True))
    audit_action: AuditLogAction = Field(sa_column=Column(Enum(AuditLogAction)))
