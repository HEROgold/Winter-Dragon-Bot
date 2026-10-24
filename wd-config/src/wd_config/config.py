"""The WinterDragon `Config` descriptor and how each scope binds its own ini file."""

lazy from typing import TYPE_CHECKING, Literal, override

lazy from confkit import Config as CKConfig
lazy from confkit.sentinels import UNSET
lazy from confkit.watcher import FileWatcher

lazy from .parser import OperatorFiles


if TYPE_CHECKING:
    lazy from pathlib import Path


class OptionalFileWatcher(FileWatcher):
    """A `FileWatcher` that treats a missing file as unchanged instead of failing to `stat` it."""

    @override
    def has_changed(self) -> bool:
        return self.filepath.exists() and super().has_changed()


class Config[T](CKConfig[T]):
    """Config descriptor for WinterDragon."""

    @classmethod
    def bind(cls, file: Path, *, operator: bool = False, optional: bool = False) -> None:
        """Give this scope its own ``file``, so no other scope's parser overwrites it.

        confkit's ``__init_subclass__`` copies the parent's parser and read-state; both are reset here so this
        scope detects its own parser and reads ``file``. ``operator`` registers ``file`` with
        :class:`OperatorFiles` for the first-launch check. ``optional`` makes the file's existence the switch:
        without it the in-code defaults apply and nothing is written; once it exists (even empty) it's read and
        confkit fills in the missing defaults.
        """
        # Pretty sure this is not required. Simply using set_file() + new subclass should be enough.
        cls.set_file(file)
        cls._parser = UNSET  # pyright: ignore[reportPrivateUsage]
        cls._has_read_config = False  # pyright: ignore[reportPrivateUsage]
        if optional:
            cls.write_on_edit = file.exists()
            cls._watcher = OptionalFileWatcher(file)  # pyright: ignore[reportPrivateUsage]
        if operator:
            OperatorFiles.register(file)

    @override
    def on_file_change(self, origin: Literal["get", "set"], old: T, new: T) -> None:
        """Re-read this scope's file, so a value edited on disk is used from its next read on, without a restart."""
        self._parser.read(self._file)  # pyright: ignore[reportPrivateUsage]
