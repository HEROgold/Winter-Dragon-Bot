from fastapi import APIRouter

from .discord import router as discord_router


router = APIRouter(prefix="/oauth", tags=["oauth"])
router.include_router(discord_router)
