
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.result_multiplayer import ResultMassiveMultiplayer

model = APIModel(ResultMassiveMultiplayer)
router = model.router
