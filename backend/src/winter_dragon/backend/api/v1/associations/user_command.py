
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.associations.user_command import AssociationUserCommand


model = APIModel(AssociationUserCommand)
router = model.router
