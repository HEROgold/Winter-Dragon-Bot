from typing import Any, Callable, Coroutine

from discord.abc import GuildChannel, PrivateChannel
from discord.app_commands import AppCommand, AppCommandGroup
from discord.channel import CategoryChannel, DMChannel, ForumChannel, GroupChannel, StageChannel, TextChannel, VoiceChannel
from discord.member import Member
from discord.role import Role
from discord.threads import Thread


type Optional[T] = T | None

type CoroutineFunction = Callable[..., Coroutine[Any, Any, Any]]
type AppCommandStore = dict[str, AppCommand | AppCommandGroup]
type MaybeGroupedAppCommand = AppCommand | AppCommandGroup | None

type MemberRole = Role | Member

type InteractionChannel = VoiceChannel | StageChannel | TextChannel | ForumChannel | CategoryChannel | Thread | DMChannel | GroupChannel
type GTPChannel = GuildChannel | Thread | PrivateChannel


type GChannel = TextChannel | VoiceChannel | StageChannel | Thread | GuildChannel
