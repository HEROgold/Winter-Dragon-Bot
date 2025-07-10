
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.game import Games


model = APIModel(Games)
router = model.router
