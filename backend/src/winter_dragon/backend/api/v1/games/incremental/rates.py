
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.incremental.rates import GeneratorRates


model = APIModel(GeneratorRates)
router = model.router
