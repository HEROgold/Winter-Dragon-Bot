from fastapi import APIRouter, status
from sqlmodel import select
from winter_dragon.database import session
from winter_dragon.database.tables.welcome import Welcome


router = APIRouter(prefix="/welcome", tags=["guilds"])

@router.get("/")
async def get_welcome(guild_id: int) -> Welcome | int:
    """Get welcome message for a guild."""
    return (
        session.exec(select(Welcome).where(Welcome.guild_id == guild_id)).first()
        or status.HTTP_404_NOT_FOUND
    )

@router.put("/")
async def set_welcome(guild_id: int, channel_id: int, message: str) -> None:
    """Set welcome message for a guild."""
    welcome = Welcome(guild_id=guild_id, channel_id=channel_id, message=message, enabled=True)
    session.add(welcome)
    session.commit()
