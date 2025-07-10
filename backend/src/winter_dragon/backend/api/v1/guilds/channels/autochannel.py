
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.autochannel import AutoChannels


model = APIModel(AutoChannels)
router = model.router

