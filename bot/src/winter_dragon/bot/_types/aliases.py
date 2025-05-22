from collections.abc import Awaitable, Callable, Coroutine, Iterable, Mapping
from typing import Any

from discord import Message, Object, PermissionOverwrite
from discord.abc import GuildChannel, PrivateChannel
from discord.app_commands import AppCommand, AppCommandGroup
from discord.channel import CategoryChannel, DMChannel, ForumChannel, GroupChannel, StageChannel, TextChannel, VoiceChannel
from discord.ext.commands.bot import AutoShardedBot, Bot
from discord.member import Member
from discord.role import Role
from discord.threads import Thread


type Optional[T] = T | None

type CoroutineFunction = Callable[..., Coroutine[Any, Any, Any]]
type AppCommandStore = dict[str, AppCommand | AppCommandGroup]

type MemberRole = Role | Member

type VocalGuildChannel = VoiceChannel | StageChannel
type InteractionChannel = (
    VoiceChannel |
    StageChannel |
    TextChannel |
    ForumChannel |
    CategoryChannel |
    Thread |
    DMChannel |
    GroupChannel
)
type PrunableChannel = VoiceChannel | StageChannel | TextChannel | Thread
type GTPChannel = GuildChannel | Thread | PrivateChannel


type GChannel = TextChannel | VoiceChannel | StageChannel | Thread | GuildChannel

type _Bot = Bot | AutoShardedBot
type MaybeAwaitable[T] = T | Awaitable[T]
type MaybeAwaitableFunc[**P, T] = Callable[P, MaybeAwaitable[T]]
type _Prefix = Iterable[str] | str
type _PrefixCallable[BotT: _Bot] = MaybeAwaitableFunc[[BotT, Message], _Prefix]
type PrefixType[BotT: _Bot] = _Prefix | _PrefixCallable[BotT]

type BotT[T: _Bot] = T

type PermissionsOverwrites = Mapping[Role | Member | Object, PermissionOverwrite]
