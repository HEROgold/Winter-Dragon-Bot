
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.commandgroup import CommandGroups


model = APIModel(CommandGroups)
router = model.router
