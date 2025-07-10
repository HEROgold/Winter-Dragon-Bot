"""Module for reminder api endpoints."""

from winter_dragon.database.extension.api_model import APIModel
from winter_dragon.database.tables.reminder import Reminder


model = APIModel(Reminder)
router = model.router
