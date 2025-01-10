from fastapi import APIRouter

from .admin import router as admin_router
from .discord_auth import router as oauth_router
from .public import router as public_router
from .user import router as user_router


router = APIRouter(prefix="/api", tags=["api"])
router.include_router(admin_router)
router.include_router(public_router)
router.include_router(user_router)
router.include_router(oauth_router)
