

from wd_db.extension.model import DiscordID


class CommandGroups(DiscordID, table=True):
    name: str
