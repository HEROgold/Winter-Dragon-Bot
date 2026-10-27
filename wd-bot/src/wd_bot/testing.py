"""Test helpers for cogs: build one to call its handlers on, without a running bot."""

lazy from types import SimpleNamespace
lazy from typing import TYPE_CHECKING, Any, cast

lazy from sqlmodel import Session

lazy from wd_bot.registry import CommandRegistry


if TYPE_CHECKING:
    lazy from collections.abc import Awaitable, Callable

    lazy from sqlalchemy import Engine

    lazy from wd_bot.bot import Bot
    lazy from wd_bot.cogs import Cog
    lazy from wd_bot.commands import Command


def detached_cog[C: Cog](cls: type[C], *, engine: Engine | None = None, **bot: object) -> C:
    """Return a ``cls`` built without :meth:`Cog.__init <wd_bot.cogs.Cog.__init__>`: no auto-load task, no hot reload.

    Its ``bot`` is a stand-in with an empty command registry and the attributes in ``bot`` (``client=...``,
    ``launch_time=...``, or another ``registry``); with an ``engine``, its session is on it. Set whatever else the
    cog's own ``__init__`` sets up.
    """
    cog = cls.__new__(cls)
    cog.bot = cast("Bot", SimpleNamespace(**{"registry": CommandRegistry(), **bot}))
    if engine is not None:
        cog.session = Session(engine)
    return cog


def cog_command(func: Callable[..., Awaitable[None]], /, **definition: Any) -> Command:  # noqa: ANN401 - Command's keywords
    """Return ``func`` as a :class:`~wd_bot.commands.Command` on a throwaway cog class, built as ``@Cog.command`` builds it.

    A command reads its options when a cog class takes it, so a handler written outside a cog needs one.
    """
    from wd_bot.cogs import Cog  # noqa: PLC0415
    from wd_bot.commands import Command  # noqa: PLC0415

    command = Command(func, **definition)
    type("TestCog", (Cog,), {"command": command}, auto_load=False)
    return command
