
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.autochannel_settings import AutoChannelSettings


model = APIModel(AutoChannelSettings)
router = model.router
