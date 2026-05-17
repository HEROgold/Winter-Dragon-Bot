

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field

from wd_db.extension.model import SQLModel
from wd_db.keys import get_foreign_key
from wd_db.tables.audit_log import AuditLog
from wd_db.tables.guild import Guilds


class GuildAuditLog(SQLModel, table=True):
    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds)), primary_key=True))
    audit_log_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(AuditLog)), primary_key=True))
