"""The one-off migration of an old ini file whose sections now belong to other scopes.

The engine knows no settings: the caller describes where each legacy section and key goes with :class:`Move`
rules, and :func:`migrate` does the rest. It works on the raw files and must run before any scope that reads
them is imported, because confkit reads a file once, when its settings class is defined.

A migration only runs when the legacy file still holds something that moves or is dropped, so a second start
does nothing. It then

1. copies the legacy file to ``<name>.bak`` (or ``<name>.bak.1``, ``.2``, ... when that exists; a backup is
   never overwritten),
2. moves each matched key to its target file and section,
3. drops every section and key no rule declares (they stay in the backup),
4. writes a value of an internal scope (a :class:`Move` with ``defaults``) only when it differs from its
   in-code default, so the internal file is created only when it carries a changed value,
5. rewrites the legacy file with only the keys whose target is the legacy file itself.

A target key is filled when it's missing or still :data:`~wd_config.parser.REQUIRED`; a real value already in
a target file is never overwritten.
"""

from __future__ import annotations

lazy import configparser
lazy import shutil
lazy from dataclasses import KW_ONLY, dataclass, field
lazy from typing import TYPE_CHECKING, override

lazy from .parser import REQUIRED


if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping
    from pathlib import Path


@dataclass(frozen=True)
class Move:
    """Where the keys of one legacy section go.

    Several moves may name the same legacy ``section``: a key goes to the move that lists it in ``keys``, else to
    the move with ``keys=None``; a key neither matches is dropped.
    """

    section: str
    """The legacy section, as written in the legacy file."""
    file: Path
    """The ini file the keys move to; the legacy file itself keeps them."""
    _: KW_ONLY
    to_section: str | None = None
    """The target section; ``None`` keeps the legacy section name."""
    keys: Mapping[str, str] | None = None
    """Legacy key (any case) -> target key; ``None`` moves every key not listed elsewhere, as written."""
    drop: Collection[str] = ()
    """Legacy keys a ``keys=None`` move drops instead of moving."""
    convert: Mapping[str, Callable[[str], str | None]] = field(default_factory=dict)
    """Legacy key -> converter of its raw value; a converter returning ``None`` drops the key."""
    defaults: Mapping[str, str] | None = None
    """Set for an internal scope: target key -> its in-code default as written; a value equal to it is dropped."""

    @property
    def target_section(self) -> str:
        """The section the keys land in."""
        return self.to_section or self.section

    def target_key(self, key: str) -> str | None:
        """Return the target key ``key`` moves to, or ``None`` when this move doesn't take it."""
        if self.keys is None:
            return None if key.lower() in {name.lower() for name in self.drop} else key
        return next((target for source, target in self.keys.items() if source.lower() == key.lower()), None)


@dataclass(frozen=True)
class MigrationReport:
    """What one migration did; every entry names a section or ``section.key``."""

    backup: Path
    """Where the untouched legacy file was copied."""
    moved: tuple[str, ...]
    """``section.key -> file:section.key`` for every value written to another file."""
    dropped: tuple[str, ...]
    """Legacy sections and keys no rule declares, or whose value couldn't be converted."""
    defaulted: tuple[str, ...]
    """Internal ``file:section.key`` values dropped because they were at their in-code default."""
    kept: tuple[str, ...]
    """Target ``file:section.key`` that already held a real value, which the legacy value didn't overwrite."""


@dataclass(frozen=True)
class _Write:
    source: str
    file: Path
    section: str
    key: str
    value: str


class _RawParser(configparser.ConfigParser):
    """Keeps keys in the case they're written in, and values verbatim."""

    def __init__(self) -> None:
        super().__init__(interpolation=None)

    @override
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def _read(file: Path) -> _RawParser:
    parser = _RawParser()
    parser.read(file, encoding="utf-8")
    return parser


def _write(parser: configparser.ConfigParser, file: Path) -> None:
    with file.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _backup_path(file: Path) -> Path:
    backup = file.with_name(f"{file.name}.bak")
    number = 0
    while backup.exists():
        number += 1
        backup = file.with_name(f"{file.name}.bak.{number}")
    return backup


def _match(moves: Iterable[Move], section: str, key: str) -> tuple[Move, str] | None:
    candidates = [move for move in moves if move.section.lower() == section.lower()]
    for move in sorted(candidates, key=lambda move: move.keys is None):
        if (target := move.target_key(key)) is not None:
            return move, target
    return None


def _plan(legacy: Path, parser: _RawParser, moves: Iterable[Move]) -> tuple[list[_Write], list[str], list[str]]:
    """Sort every legacy key into writes, drops and internal values at default; all empty when nothing changes."""
    moves = list(moves)
    writes: list[_Write] = []
    dropped: list[str] = []
    defaulted: list[str] = []
    for section in parser.sections():
        if not any(move.section.lower() == section.lower() for move in moves):
            dropped.append(section)
            continue
        for key, raw in parser[section].items():
            name = f"{section}.{key}"
            matched = _match(moves, section, key)
            if matched is None:
                dropped.append(name)
                continue
            move, target = matched
            convert = next((fn for source, fn in move.convert.items() if source.lower() == key.lower()), None)
            value = convert(raw) if convert else raw
            if value is None:
                dropped.append(name)
            elif move.defaults is not None and move.defaults.get(target) == value:
                defaulted.append(f"{move.file}:{move.target_section}.{target}")
            else:
                writes.append(_Write(name, move.file, move.target_section, target, value))
    unchanged = all(write.file == legacy and write.source == f"{write.section}.{write.key}" for write in writes)
    if unchanged and not dropped and not defaulted:
        return [], [], []
    return writes, dropped, defaulted


def _fill(file: Path, writes: Iterable[_Write]) -> list[str]:
    """Write ``writes`` into ``file`` where a key is missing or still required; return the keys kept instead."""
    parser = _read(file)
    kept: list[str] = []
    for write in writes:
        if not parser.has_section(write.section):
            parser.add_section(write.section)
        existing = next((key for key in parser[write.section] if key.lower() == write.key.lower()), None)
        if existing is not None and parser[write.section][existing].strip() != REQUIRED:
            kept.append(f"{file}:{write.section}.{write.key}")
            continue
        if existing is not None:
            parser.remove_option(write.section, existing)
        parser.set(write.section, write.key, write.value)
    _write(parser, file)
    return kept


def migrate(legacy: Path, moves: Iterable[Move]) -> MigrationReport | None:
    """Migrate ``legacy`` by ``moves``; ``None`` when it holds nothing to move or drop (or doesn't exist)."""
    if not legacy.exists():
        return None
    parser = _read(legacy)
    writes, dropped, defaulted = _plan(legacy, parser, moves)
    if not writes and not dropped and not defaulted:
        return None

    backup = _backup_path(legacy)
    shutil.copy2(legacy, backup)

    kept: list[str] = []
    others = [write for write in writes if write.file != legacy]
    for file in dict.fromkeys(write.file for write in others):
        kept += _fill(file, (write for write in others if write.file == file))

    rewritten = _RawParser()
    for write in writes:
        if write.file == legacy:
            if not rewritten.has_section(write.section):
                rewritten.add_section(write.section)
            rewritten.set(write.section, write.key, write.value)
    _write(rewritten, legacy)

    return MigrationReport(
        backup=backup,
        moved=tuple(f"{write.source} -> {write.file}:{write.section}.{write.key}" for write in others),
        dropped=tuple(dropped),
        defaulted=tuple(defaulted),
        kept=tuple(kept),
    )
