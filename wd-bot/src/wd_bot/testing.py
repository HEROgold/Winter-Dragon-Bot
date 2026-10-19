"""Test helpers for cogs: build one to call its handlers on, without a running bot."""

from __future__ import annotations

lazy from types import SimpleNamespace
lazy from typing import TYPE_CHECKING, cast

lazy from sqlmodel import Session

lazy from wd_bot.registry import CommandRegistry


if TYPE_CHECKING:
    lazy from sqlalchemy import Engine

    lazy from wd_bot.bot import Bot
    lazy from wd_bot.cogs import Cog


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
