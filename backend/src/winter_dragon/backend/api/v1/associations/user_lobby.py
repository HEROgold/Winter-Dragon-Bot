
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.associations.user_lobby import AssociationUserLobby


model = APIModel(AssociationUserLobby)
router = model.router
