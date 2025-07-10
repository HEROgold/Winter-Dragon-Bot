
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.welcome import Welcome


model = APIModel(Welcome)
router = model.router
