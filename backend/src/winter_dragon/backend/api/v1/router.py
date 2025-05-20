"""Main router for the Winter Dragon Bot API v1.

This module aggregates all API route modules and exposes them under /api/v1.
"""

from fastapi import APIRouter

from .auth.routes import router as auth_router
from .features.routes import router as features_router
from .servers.routes import router as servers_router
from .statistics.routes import router as statistics_router
from .system.routes import router as system_router
from .users.routes import router as users_router


# Main v1 API router
api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(servers_router, prefix="/servers", tags=["servers"])
api_router.include_router(features_router, tags=["features"])
api_router.include_router(statistics_router, tags=["statistics"])
api_router.include_router(system_router, tags=["system"])
