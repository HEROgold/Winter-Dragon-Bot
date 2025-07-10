
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.wyr_question import WyrQuestion


model = APIModel(WyrQuestion)
router = model.router
