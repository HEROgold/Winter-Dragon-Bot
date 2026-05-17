

from wd_db.extension.model import DiscordID


class Roles(DiscordID, table=True):
    name: str
