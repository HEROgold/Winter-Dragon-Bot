from datetime import datetime
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


class Sale(TypedDict):
    title: str
    url: str
    sale_percent: int
    final_price: float
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime


class TeamDict(TypedDict):
    id: int
    members: list[Member]
