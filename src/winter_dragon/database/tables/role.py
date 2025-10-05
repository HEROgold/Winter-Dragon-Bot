
from winter_dragon.database.extension.model import DiscordID


class Roles(DiscordID, table=True):
    name: str
