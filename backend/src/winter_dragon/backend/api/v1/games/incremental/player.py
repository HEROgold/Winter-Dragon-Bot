
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.incremental.player import Players


model = APIModel(Players)
router = model.router
