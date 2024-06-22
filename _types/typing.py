
from datetime import datetime
from typing import Any, Callable, Coroutine, TypedDict

from discord.abc import GuildChannel, PrivateChannel
from discord.app_commands import AppCommand
from discord.channel import CategoryChannel, DMChannel, ForumChannel, GroupChannel, StageChannel, TextChannel, VoiceChannel
from discord.member import Member
from discord.role import Role
from discord.threads import Thread
from discord.user import User


type MISSING[T] = T | None
type Optional[T] = T | MISSING[T]

CoroutineFunction = Callable[..., Coroutine[Any, Any, Any]]
AppCommandStore = dict[str, AppCommand]

MemberRole = Role | Member

InteractionChannel = (
    VoiceChannel
    | StageChannel
    | TextChannel
    | ForumChannel
    | CategoryChannel
    | Thread
    | DMChannel
    | GroupChannel
)
GTPChannel = GuildChannel | Thread | PrivateChannel


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
    final_price: int
    is_dlc: bool
    is_bundle: bool
    update_datetime: datetime

class TeamDict(TypedDict):
    id: int
    members: list[User | Member]
