
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.lobbystatus import LobbyStatus


model = APIModel(LobbyStatus)
router = model.router
