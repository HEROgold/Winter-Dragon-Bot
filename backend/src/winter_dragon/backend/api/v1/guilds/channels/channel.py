from collections.abc import Sequence

from fastapi import APIRouter, status
from sqlmodel import select
from winter_dragon.database import session
from winter_dragon.database.tables.channel import Channels
from winter_dragon.database.tables.message import Messages


router = APIRouter(prefix="/channels/{channel_id}", tags=["channels"])

@router.get("/")
async def get_channel(channel_id: int) -> Channels | int:
    """Get channel by ID."""
    return (
        session.exec(select(Channels).where(Channels.id == channel_id)).first()
        or status.HTTP_404_NOT_FOUND
    )

@router.get("/messages")
async def get_messages(channel_id: int) -> Sequence[Messages]:
    """Get messages from a channel."""
    return session.exec(
        select(Messages).where(Messages.channel_id == channel_id),
    ).all()
