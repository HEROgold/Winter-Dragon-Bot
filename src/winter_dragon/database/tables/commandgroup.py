from __future__ import annotations

from winter_dragon.database.extension.model import DiscordID


class CommandGroups(DiscordID, table=True):
    name: str
