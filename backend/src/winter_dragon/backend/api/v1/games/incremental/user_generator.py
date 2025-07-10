
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.incremental.user_generator import AssociationUserGenerator


model = APIModel(AssociationUserGenerator)
router = model.router
