
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field
from winter_dragon.database.extension.model import SQLModel
from winter_dragon.database.keys import get_foreign_key
from winter_dragon.database.tables.audit_log import AuditLog
from winter_dragon.database.tables.guild import Guilds


class GuildAuditLog(SQLModel, table=True):

    guild_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(Guilds, "id")), primary_key=True))
    audit_log_id: int = Field(sa_column=Column(ForeignKey(get_foreign_key(AuditLog, "id")), primary_key=True))
