
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.associations.user_hangman import AssociationUserHangman


model = APIModel(AssociationUserHangman)
router = model.router
