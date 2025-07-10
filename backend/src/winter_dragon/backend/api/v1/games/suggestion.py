
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.suggestion import Suggestions


model = APIModel(Suggestions)
router = model.router
