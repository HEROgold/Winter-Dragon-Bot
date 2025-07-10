
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.disabled_commands import DisabledCommands


model = APIModel(DisabledCommands)
router = model.router
