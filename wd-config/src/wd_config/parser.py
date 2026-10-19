"""The first-launch check: operator-facing ini files must have every required value filled in."""

from __future__ import annotations

lazy import configparser
lazy from typing import TYPE_CHECKING, ClassVar, override

lazy from .errors import FirstTimeLaunchError


if TYPE_CHECKING:
    lazy from collections.abc import Generator
    lazy from pathlib import Path


REQUIRED = "!!"
"""Default of a setting the operator must fill in before the bot can start."""


def required(hint: str) -> str:
    """Return a :data:`REQUIRED` default followed by ``hint``, such as the URL the operator finds the value at."""
    return f"{REQUIRED} {hint}"


def is_required(value: str) -> bool:
    """Whether ``value`` is still a :data:`REQUIRED` default, with or without a hint."""
    return value.strip().startswith(REQUIRED)


class _CaseKeepingParser(configparser.ConfigParser):
    """Reports keys with their case as written, not lowercased."""

    @override
    def optionxform(self, optionstr: str) -> str:
        return optionstr


class OperatorFiles:
    """The ini files an operator edits; each scope with operator settings registers its file here."""

    _files: ClassVar[list[Path]] = []

    @classmethod
    def register(cls, file: Path) -> None:
        """Check ``file`` on first launch; a scope calls this once, next to its ``set_file``."""
        if file not in cls._files:
            cls._files.append(file)

    @classmethod
    def unset(cls) -> Generator[str]:
        """Yield ``file:section:key`` for every value still at the :data:`REQUIRED` default."""
        for file in cls._files:
            parser = _CaseKeepingParser(interpolation=None)
            parser.read(file, encoding="utf-8")
            for section in parser.sections():
                for key, value in parser[section].items():
                    if is_required(value):
                        yield f"{file}:{section}:{key}"

    @classmethod
    def check(cls) -> None:
        """Raise :class:`FirstTimeLaunchError` listing every required value the operator hasn't filled in."""
        if unset := list(cls.unset()):
            msg = f"First time launch detected, please fill in these settings (still {REQUIRED}): {', '.join(unset)}"
            raise FirstTimeLaunchError(msg)
