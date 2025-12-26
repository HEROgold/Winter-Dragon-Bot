"""File-watcher based hot reload utilities for Discord cogs."""

from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from enum import IntEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from herogold.log import LoggerMixin

from winter_dragon.bot.core.settings import Settings


if TYPE_CHECKING:
    from winter_dragon.bot.core.bot import WinterDragon
    from winter_dragon.discord.cogs import Cog


class WatcherFlags(IntEnum):
    """States for the auto-reload watcher."""

    Enabled = auto()
    """Flag to indicate that the watcher is enabled."""
    Registered = auto()
    """Flag to indicate that the watcher is currently registered to a cog."""

    @property
    def is_enabled(self) -> bool:
        """Check if the Enabled flag is set."""
        return bool(self & WatcherFlags.Enabled)


default_flags = WatcherFlags.Enabled


@dataclass(slots=True)
class _WatchEntry:
    """Runtime data required to watch and reload an extension module."""

    bot: WinterDragon
    path: Path
    task: asyncio.Task[None]
    refs: int
    mtime_ns: int
    logger: logging.Logger


class AutoReloadWatcher(LoggerMixin):
    """Monitors extension files and reloads them in-place when they change."""

    _entries: ClassVar[dict[str, _WatchEntry]] = {}

    def __init__(self, *, bot: WinterDragon, cog_cls: type[Cog], flags: WatcherFlags = default_flags) -> None:
        """Initialize the auto-reload watcher for a specific cog class."""
        self.bot = bot
        self.cog_cls = cog_cls
        self.module_name = cog_cls.__module__
        self.flags = flags

    # Tech Debt: Replace all callers with bitfield checks
    @property
    def _registered(self) -> bool:
        """Indicates whether the watcher is currently registered."""
        return (self.flags & WatcherFlags.Registered) != 0

    @_registered.setter
    def _registered(self, value: bool) -> None:
        if value:
            self.flags |= WatcherFlags.Registered
        else:
            self.flags &= ~WatcherFlags.Registered

    def register(self) -> None:
        """Start watching the cog's backing module."""
        if self._registered or not self._should_watch():
            return
        path = self._resolve_module_path()
        if path is None:
            return
        entry = AutoReloadWatcher._entries.get(self.module_name)
        if entry:
            entry.refs += 1
            self._registered = True
            return
        task = self.bot.loop.create_task(self._watch_extension_file(self.module_name))
        AutoReloadWatcher._entries[self.module_name] = _WatchEntry(
            bot=self.bot,
            path=path,
            task=task,
            refs=1,
            mtime_ns=self._get_file_mtime(path),
            logger=self.logger,
        )
        self._registered = True
        self.logger.debug("Enabled auto-reload watcher for %s (%s)", self.module_name, path)

    def deregister(self) -> None:
        """Stop watching the module when no cogs reference it anymore."""
        if not self._registered:
            return
        entry = AutoReloadWatcher._entries.get(self.module_name)
        if entry is None:
            self._registered = False
            return
        entry.refs -= 1
        if entry.refs <= 0:
            AutoReloadWatcher._entries.pop(self.module_name, None)
            try:
                current_task = asyncio.current_task()
            except RuntimeError:
                current_task = None
            if entry.task is not current_task:
                entry.task.cancel()
        self._registered = False

    def _should_watch(self) -> bool:
        return (
            self.flags.is_enabled
            and Settings.auto_reload_extensions
            and self.module_name.startswith("winter_dragon.bot.extensions")
        )

    def _resolve_module_path(self) -> Path | None:
        try:
            return Path(inspect.getfile(self.cog_cls)).resolve()
        except (OSError, TypeError) as exc:
            self.logger.warning(
                "Cannot enable auto-reload for %s because its file path could not be resolved: %s",
                self.module_name,
                exc,
            )
            return None

    @staticmethod
    def _get_file_mtime(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return 0

    @classmethod
    async def _watch_extension_file(cls, module_name: str) -> None:
        interval = float(Settings.auto_reload_poll_seconds or 1.5)
        if interval <= 0:
            interval = 1.5
        try:
            while True:
                entry = cls._entries.get(module_name)
                if entry is None:
                    return
                await asyncio.sleep(interval)
                entry = cls._entries.get(module_name)
                if entry is None:
                    return
                current_mtime = cls._get_file_mtime(entry.path)
                if current_mtime <= entry.mtime_ns:
                    continue
                entry.mtime_ns = current_mtime
                await cls._reload_extension(entry.bot, module_name, entry.logger)
        except asyncio.CancelledError:
            cls._log_with_fallback(module_name, "debug", "Stopped watching %s for changes", module_name)
            raise
        except Exception:  # noqa: BLE001
            cls._log_with_fallback(module_name, "exception", "Auto-reload watcher for %s crashed", module_name)

    @classmethod
    def _log_with_fallback(cls, module_name: str, level: str, msg: str, *args: object) -> None:
        entry = cls._entries.get(module_name)
        logger = entry.logger if entry else logging.getLogger(f"{__name__}.{cls.__name__}")
        getattr(logger, level)(msg, *args)

    @staticmethod
    async def _reload_extension(bot: WinterDragon, module_name: str, logger: logging.Logger) -> None:
        logger.info("Detected change in %s. Reloading extension.", module_name)
        try:
            reload_result = bot.reload_extension(module_name)
            if inspect.isawaitable(reload_result):
                await reload_result
        except Exception:
            logger.exception("Failed to reload extension %s", module_name)
