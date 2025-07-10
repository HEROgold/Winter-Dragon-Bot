
from fastapi import APIRouter
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.channel import Channels


model = APIModel(Channels)
router = model.router

sub_router = APIRouter(prefix="/{id_:int}")
router.include_router(sub_router)
