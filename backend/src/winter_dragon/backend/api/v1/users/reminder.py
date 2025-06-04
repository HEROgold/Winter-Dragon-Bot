"""Module for reminder api endpoints."""

from fastapi import APIRouter, status
from sqlmodel import select
from winter_dragon.database import session
from winter_dragon.database.tables.reminder import Reminder


router = APIRouter(prefix="/reminders", tags=["reminder"])


@router.get("/{reminder_id}")
async def get_reminder(reminder_id: int) -> Reminder | int:
    """Get reminder by ID."""
    return (
        session.exec(select(Reminder).where(Reminder.id == reminder_id)).first()
        or status.HTTP_404_NOT_FOUND
    )
