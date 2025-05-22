from collections.abc import Sequence

from fastapi import APIRouter, status
from sqlmodel import select
from winter_dragon.database import session
from winter_dragon.database.tables.associations.guild_audit_log import GuildAuditLog
from winter_dragon.database.tables.associations.guild_roles import GuildRoles
from winter_dragon.database.tables.audit_log import AuditLog
from winter_dragon.database.tables.auto_assign_role import AutoAssignRole
from winter_dragon.database.tables.auto_reassign import AutoReAssign
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.guild import Guilds
from winter_dragon.database.tables.role import Roles

from .channels.channel import router as channel_router
from .welcome import router as welcome_router


router = APIRouter(prefix="/guilds/{guild_id}", tags=["guilds"])
router.include_router(channel_router)
router.include_router(welcome_router)


@router.get("/")
async def get_guild(guild_id: int) -> Guilds | int:
    """Get guild by ID."""
    return (
        session.exec(select(Guilds).where(Guilds.id == guild_id)).first()
        or status.HTTP_404_NOT_FOUND
    )

@router.get("/channels")
async def get_channels(guild_id: int) -> Sequence[Channels]:
    """Get channels for a guild."""
    return session.exec(
        select(Channels).where(Channels.guild_id == guild_id),
    ).all()

@router.get("/roles")
async def get_roles(guild_id: int) -> Sequence[Roles]:
    """Get all roles for a guild."""
    return session.exec(
        select(Roles).join(GuildRoles).where(GuildRoles.guild_id == guild_id),
    ).all()

@router.get("/roles/reassign")
async def get_roles_reassign(guild_id: int) -> AutoReAssign | 404:
    """Get all roles for a guild."""
    return session.exec(
        select(AutoReAssign).where(AutoReAssign.guild_id == guild_id),
    ).first() or 404

@router.get("/roles/auto_assign")
async def get_roles_auto_assign(guild_id: int) -> Sequence[AutoAssignRole]:
    """Get the automatically assigned roles for a guild."""
    return session.exec(
        select(AutoAssignRole).where(AutoAssignRole.guild_id == guild_id),
    ).all()

@router.get("/audit_logs")
async def get_audit_logs(guild_id: int) -> Sequence[AuditLog]:
    """Get all audit logs for a guild."""
    return session.exec(
        select(AuditLog).join(GuildAuditLog).where(GuildAuditLog.guild_id == guild_id),
    ).all()
