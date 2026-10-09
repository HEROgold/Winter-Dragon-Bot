"""Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency."""

from __future__ import annotations

lazy from enum import IntFlag, auto
lazy from typing import TYPE_CHECKING, ClassVar, NotRequired, Required, Self, TypedDict, Unpack, override

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Session, SQLModel
lazy from wd_db.constants import engine
lazy from wd_discord.snowflake import Snowflake

lazy from wd_bot.auto_reload import AutoReloadWatcher
lazy from wd_bot.commands import Command, CommandGroup
lazy from wd_bot.components import ComponentHandler
lazy from wd_bot.listener import listener
lazy from wd_bot.registry import CommandPath


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator, Iterable

    lazy from sqlalchemy import Connection, Engine
    lazy from wd_discord.interactions import InteractionContextType
    lazy from wd_discord.permissions import Permissions
    lazy from wd_discord.snowflake import SnowflakeLike

    lazy from wd_bot.bot import Bot
    lazy from wd_bot.commands import AppCommand
    lazy from wd_bot.registry import CommandMention


def command(
    name: str,
    description: str,
    default_member_permissions: Permissions | None = None,
    contexts: Iterable[InteractionContextType] | None = None,
    guild_ids: Iterable[SnowflakeLike] | None = None,
) -> Callable[[Callable[..., Awaitable[None]]], Command]:
    """Tag a Cog method as a chat-input application command, building a :class:`Command` for it.

    ``guild_ids`` registers the command in just those guilds instead of globally; on a :class:`GroupCog`
    the group's ``guild_ids`` apply instead.
    """

    def decorator(func: Callable[..., Awaitable[None]]) -> Command:
        return Command(
            func,
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
            contexts=contexts,
            guild_ids=guild_ids,
        )

    return decorator


def component(prefix: str) -> Callable[[Callable[..., Awaitable[None]]], ComponentHandler]:
    """Tag a Cog method as the handler for components whose ``custom_id`` starts with ``prefix``."""

    def decorator(func: Callable[..., Awaitable[None]]) -> ComponentHandler:
        return ComponentHandler(func, prefix=prefix)

    return decorator


class BotArgs(TypedDict):
    """TypedDict for bot arguments."""

    bot: Required[Bot]
    db_session: NotRequired[Session]


class CogFlags(IntFlag):
    """Flags for Cog behavior."""

    AutoLoad = auto()
    """Flag to indicate that the cog should be auto-loaded."""
    AutoReload = auto()
    """Flag to indicate that the cog should be auto-reloaded on file changes."""


default_flags = CogFlags.AutoLoad | CogFlags.AutoReload


class Cog(LoggerMixin):
    """A wd-native feature unit: a class whose methods can be tagged with @Cog.listener()."""

    bot: Bot
    flags: CogFlags = default_flags
    __cog_name__: ClassVar[str]
    # Deliberately not staticmethod(listener): `Cog.listener(...)` is always accessed via the
    # class (never an instance) at class-body-decoration time, so a plain function attribute
    # already behaves correctly without it - and `ty` currently loses @overload resolution on a
    # staticmethod-wrapped overloaded function (confirmed: identical overloads type-check fine
    # as a bare class attribute, wrong as soon as staticmethod() wraps them).
    listener = listener
    command = command
    component = component

    def __init__(self, **kwargs: Unpack[BotArgs]) -> None:
        """Initialize the Cog instance with a bot reference and a database session."""
        self.bot = kwargs["bot"]
        self.session = kwargs.get("db_session", Session(engine))
        self._auto_reloader = AutoReloadWatcher(bot=self.bot, cog_cls=type(self))

        # Don't start the auto_load loop for the abstract/base Cog classes
        # (we only want concrete subclasses to be able to auto-load themselves).
        if self.__class__ not in (Cog, GroupCog):
            self.bot.loop.create_task(self.auto_load())
            self._auto_reloader.register()

    def __init_subclass__(cls: type[Self], *, auto_load: bool = True, flags: CogFlags | None = None) -> None:
        """Configure loader and hot-reload behavior for subclasses."""
        super().__init_subclass__()
        cls.__cog_name__ = cls.__name__
        if flags:
            cls.flags = flags
        if auto_load:
            cls.flags |= CogFlags.AutoLoad
        else:
            cls.flags &= ~CogFlags.AutoLoad

    async def auto_load(self) -> None:
        """Load the cog if auto_load is True."""
        if self.__cog_name__ in self.bot.cogs:
            return
        if self.flags & CogFlags.AutoLoad:
            self.logger.debug(t"Auto loaded Cog {type(self).__name__}")
            await self.bot.add_cog(self)

    @classmethod
    def commands(cls) -> Generator[Command]:
        """Yield the :class:`Command` attributes defined on this cog class or inherited from its bases."""
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, Command):
                yield attr

    @classmethod
    def app_commands(cls) -> Generator[AppCommand]:
        """Yield what this cog registers as top-level Discord commands: each of its commands."""
        yield from cls.commands()

    @classmethod
    def components(cls) -> Generator[ComponentHandler]:
        """Yield the :class:`ComponentHandler` attributes defined on this cog class or inherited from its bases."""
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, ComponentHandler):
                yield attr

    @classmethod
    def path_of(cls, command: Command) -> CommandPath:
        """Return the path a user types to run ``command`` from this cog: ``/name``."""
        return CommandPath(command.name)

    def mention(self, command: Command, *, guild: SnowflakeLike | None = None) -> CommandMention:
        """Return a mention of ``command``, as seen from ``guild``: clickable once Discord reported it, else ``/name``.

        ``command`` may belong to another cog; its path comes from the cog class it was defined on.
        """
        own = any(candidate is command for candidate in type(self).commands())
        owner = type(self) if own or command.owner is None else command.owner
        guild_id = None if guild is None else Snowflake.coerce(guild)
        return self.bot.registry.mention(owner.path_of(command), guild_id)

    @property
    def bind(self) -> Engine | Connection:
        """The database the cog's injected session connects to; open short-lived sessions on it per operation."""
        return self.session.get_bind()

    def create_tables(self, *models: type[SQLModel]) -> None:
        """Create the tables of ``models`` that don't exist yet, in :attr:`bind`; each named after its model, lowercased."""
        tables = [SQLModel.metadata.tables[model.__name__.lower()] for model in models]
        SQLModel.metadata.create_all(self.bind, tables=tables)

    async def load(self) -> None:
        """Run setup once registered with the bot; a hook for subclasses to override.

        No-op by default: there's no CommandTree yet to sync app commands against.
        """

    async def unload(self) -> None:
        """Unregister any auto-reload watcher."""
        self._auto_reloader.deregister()


class GroupCog(Cog):
    """A cog whose commands are registered as subcommands of one Discord command, ``/<group_name> <command>``.

    Configure the group with class keywords::

        class BotCommands(GroupCog, name="bot-commands", description="...", default_member_permissions=...):

    ``name`` defaults to the class name in kebab-case and ``description`` to the first line of the class
    docstring. ``default_member_permissions``, ``contexts`` and ``guild_ids`` apply to the whole group (Discord
    has none of them per subcommand).
    """

    group_name: ClassVar[str]
    group_description: ClassVar[str]
    group_default_member_permissions: ClassVar[Permissions | None] = None
    group_contexts: ClassVar[list[InteractionContextType] | None] = None
    group_guild_ids: ClassVar[list[SnowflakeLike] | None] = None

    def __init_subclass__(  # noqa: PLR0913 - each keyword is a class-level group setting
        cls: type[Self],
        *,
        name: str | None = None,
        description: str | None = None,
        default_member_permissions: Permissions | None = None,
        contexts: Iterable[InteractionContextType] | None = None,
        guild_ids: Iterable[SnowflakeLike] | None = None,
        auto_load: bool = True,
        flags: CogFlags | None = None,
    ) -> None:
        """Configure the subcommand group, plus the usual loader and hot-reload behavior."""
        super().__init_subclass__(auto_load=auto_load, flags=flags)
        cls.group_name = name or _kebab_case(cls.__name__)
        cls.group_description = description or (cls.__doc__ or cls.__name__).strip().splitlines()[0]
        cls.group_default_member_permissions = default_member_permissions
        cls.group_contexts = None if contexts is None else list(contexts)
        cls.group_guild_ids = None if guild_ids is None else list(guild_ids)

    @classmethod
    def app_commands(cls) -> Generator[AppCommand]:
        """Yield this cog's single top-level Discord command: the group holding its commands."""
        yield CommandGroup(
            name=cls.group_name,
            description=cls.group_description,
            subcommands=cls.commands(),
            default_member_permissions=cls.group_default_member_permissions,
            contexts=cls.group_contexts,
            guild_ids=cls.group_guild_ids,
        )

    @classmethod
    @override
    def path_of(cls, command: Command) -> CommandPath:
        """Return the path a user types to run the subcommand ``command``: ``/<group> <command>``."""
        return CommandPath(cls.group_name, command.name)


def _kebab_case(name: str) -> str:
    """Turn a class name like ``BotCommands`` (or ``_BotCommands``) into a Discord command name like ``bot-commands``."""
    name = name.lstrip("_")
    return "".join(f"-{char.lower()}" if char.isupper() and index else char.lower() for index, char in enumerate(name))
