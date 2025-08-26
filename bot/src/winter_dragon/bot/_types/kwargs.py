from typing import NotRequired, Required, TypedDict

from sqlmodel import Session
from winter_dragon.bot.core.bot import WinterDragon


class BotArgs(TypedDict):
    bot: Required[WinterDragon]
    db_session: NotRequired[Session]
