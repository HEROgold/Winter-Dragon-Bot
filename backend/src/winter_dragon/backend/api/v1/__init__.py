"""First version of the API."""

from fastapi import APIRouter

from .guilds.guild import router as guild_router
from .users.reminder import router as reminder_router
from .users.user import router as user_router


router = APIRouter(prefix="/api/v1")
router.include_router(user_router)
router.include_router(reminder_router)
router.include_router(guild_router)
