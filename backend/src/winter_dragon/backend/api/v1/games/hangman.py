
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.hangman import Hangmen


model = APIModel(Hangmen)
router = model.router
