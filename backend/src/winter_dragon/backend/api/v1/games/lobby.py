
from __future__ import annotations

from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.lobby import Lobbies


model = APIModel(Lobbies)
router = model.router
