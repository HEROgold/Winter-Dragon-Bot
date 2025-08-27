from typing import TypedDict

from discord.member import Member


class FileData(TypedDict):
    filepath: str
    cog_path: str
    edit_time: float


class CogData(TypedDict):
    timestamp: float
    files: dict[str, FileData]
    edited: dict[str, FileData]

class TeamDict(TypedDict):
    id: int
    members: list[Member]
