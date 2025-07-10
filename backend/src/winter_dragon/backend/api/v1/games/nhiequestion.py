
from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.nhiequestion import NhieQuestion


model = APIModel(NhieQuestion)
router = model.router
