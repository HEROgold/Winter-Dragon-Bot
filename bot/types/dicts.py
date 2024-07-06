from datetime import datetime
from typing import TypedDict

from discord.member import Member
from discord.user import User

from bot.types.dicts import FileData


class AccessToken(TypedDict):
    user_id: int
    access_token: str
    refresh_token: str
    created_at: datetime
    expires_in: int
    expires_at: datetime
    token_type: str
    scope: str


class CogData(TypedDict):
    timestamp: float
    files: dict[str, FileData]
    edited: dict[str, FileData]


class Sale(TypedDict):
    title: str
    url: str
    sale_percent: int
    final_price: int
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime


class TeamDict(TypedDict):
    id: int
    members: list[User | Member]


class FileData(TypedDict):
    filepath: str
    cog_path: str
    edit_time: float
