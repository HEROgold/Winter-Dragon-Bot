
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.lookingforgroup import LookingForGroup


model = APIModel(LookingForGroup)
router = model.router
