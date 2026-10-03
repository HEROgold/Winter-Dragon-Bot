"""Module that contains Cogs: wd-native feature units with no discord.ext.commands dependency."""

from __future__ import annotations

lazy from enum import IntFlag, auto
lazy from typing import TYPE_CHECKING, ClassVar, NotRequired, Required, Self, TypedDict, Unpack

lazy from herogold.log import LoggerMixin
lazy from sqlmodel import Session
lazy from wd_db.constants import engine

lazy from wd_bot.auto_reload import AutoReloadWatcher
lazy from wd_bot.commands import Command, CommandGroup
lazy from wd_bot.listener import listener


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable, Generator

    lazy from wd_discord.permissions import Permissions

    lazy from wd_bot.bot import Bot
    lazy from wd_bot.commands import AppCommand


def command(
    name: str,
    description: str,
    default_member_permissions: Permissions | None = None,
) -> Callable[[Callable[..., Awaitable[None]]], Command]:
    """Tag a Cog method as a chat-input application command, building a :class:`Command` for it."""

    def decorator(func: Callable[..., Awaitable[None]]) -> Command:
        return Command(
            func,
            name=name,
            description=description,
            default_member_permissions=default_member_permissions,
        )

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
    docstring. ``default_member_permissions`` applies to the whole group (Discord has none per subcommand).
    """

    group_name: ClassVar[str]
    group_description: ClassVar[str]
    group_default_member_permissions: ClassVar[Permissions | None] = None

    def __init_subclass__(
        cls: type[Self],
        *,
        name: str | None = None,
        description: str | None = None,
        default_member_permissions: Permissions | None = None,
        auto_load: bool = True,
        flags: CogFlags | None = None,
    ) -> None:
        """Configure the subcommand group, plus the usual loader and hot-reload behavior."""
        super().__init_subclass__(auto_load=auto_load, flags=flags)
        cls.group_name = name or _kebab_case(cls.__name__)
        cls.group_description = description or (cls.__doc__ or cls.__name__).strip().splitlines()[0]
        cls.group_default_member_permissions = default_member_permissions

    @classmethod
    def app_commands(cls) -> Generator[AppCommand]:
        """Yield this cog's single top-level Discord command: the group holding its commands."""
        yield CommandGroup(
            name=cls.group_name,
            description=cls.group_description,
            subcommands=cls.commands(),
            default_member_permissions=cls.group_default_member_permissions,
        )


def _kebab_case(name: str) -> str:
    """Turn a class name like ``BotCommands`` (or ``_BotCommands``) into a Discord command name like ``bot-commands``."""
    name = name.lstrip("_")
    return "".join(f"-{char.lower()}" if char.isupper() and index else char.lower() for index, char in enumerate(name))
