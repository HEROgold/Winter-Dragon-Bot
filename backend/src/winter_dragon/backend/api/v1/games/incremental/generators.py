
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.incremental.generators import Generators


model = APIModel(Generators)
router = model.router
