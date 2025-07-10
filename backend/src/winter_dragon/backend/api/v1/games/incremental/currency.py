
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.incremental.currency import UserMoney


model = APIModel(UserMoney)
router = model.router
