"""
This module defines the API endpoints for the Winter Dragon Bot using FastAPI and Herogold.
It dynamically generates API routes based on the SQLModel models defined in the application.
"""  # noqa: D205, D212, D404

from fastapi import APIRouter
from herogold.orm.api_model import APIModel
from herogold.orm.model import models

from winter_dragon.models import *  # noqa: F403 # Import all models to ensure they are registered


router = APIRouter(prefix="/api/v1", tags=["API"])

for model in models:
    sub_router = APIRouter(prefix=f"/{model.__tablename__}")
    x = APIModel(model, sub_router)
    router.include_router(sub_router)
