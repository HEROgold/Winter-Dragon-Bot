from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.command import Commands


model = APIModel(Commands)
router = model.router
