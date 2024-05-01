
from datetime import datetime
from typing import Any, Callable, Coroutine, TypedDict

from discord import CategoryChannel, DMChannel, ForumChannel, GroupChannel, Member, Role, StageChannel, TextChannel, Thread, User, VoiceChannel
from discord.abc import GuildChannel, PrivateChannel
from discord.app_commands import AppCommand


type MISSING[T] = T | None
type Optional[T] = T | MISSING[T]

type CoroutineFunction = Callable[..., Coroutine[Any, Any, Any]]
type AppCommandStore = dict[str, AppCommand]

type MemberRole = Role | Member

type InteractionChannel = (
    VoiceChannel
    | StageChannel
    | TextChannel
    | ForumChannel
    | CategoryChannel
    | Thread
    | DMChannel
    | GroupChannel
)
type GTPChannel = GuildChannel | Thread | PrivateChannel


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
