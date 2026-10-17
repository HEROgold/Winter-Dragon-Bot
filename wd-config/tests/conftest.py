"""Boot wd-config in a fresh Python process inside a temp directory and report what it resolved and wrote.

confkit binds descriptors and writes defaults when a settings class is defined, and keeps its parser state
on the class, so a boot can't be reset or repeated in-process. Each boot is a new interpreter run with the
temp directory as its working directory, which is where wd-config resolves its relative ini paths.
"""

from __future__ import annotations

lazy import configparser
lazy import json
lazy import subprocess
lazy import sys
lazy import textwrap
lazy from dataclasses import dataclass
lazy from typing import TYPE_CHECKING, Any, Protocol, override

lazy import pytest


if TYPE_CHECKING:
    lazy from collections.abc import Mapping
    lazy from pathlib import Path


_MARKER = "@@wd-config-boot@@"


@dataclass(frozen=True)
class Boot:
    """What one boot produced."""

    values: dict[str, Any]
    """The `result` dict the boot code built, round-tripped through JSON."""
    files: dict[str, dict[str, dict[str, str]]]
    """Every ini file in the directory after the boot: filename -> section -> key -> raw value."""


class BootConfig(Protocol):
    """Run `code` in a fresh interpreter in the test's temp directory, after writing `files` there."""

    def __call__(self, code: str, *, files: Mapping[str, str] | None = None) -> Boot:
        """`code` must bind a JSON-serialisable dict named `result`; `files` maps ini filename -> contents."""
        ...


class _RawIniParser(configparser.ConfigParser):
    """Reads keys with their case as written, not lowercased."""

    @override
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def _read_ini(path: Path) -> dict[str, dict[str, str]]:
    parser = _RawIniParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    return {section: dict(parser[section]) for section in parser.sections()}


def boot(directory: Path, code: str, *, files: Mapping[str, str] | None = None) -> Boot:
    """Write `files` into `directory`, run `code` there in a fresh interpreter and collect the outcome."""
    for name, contents in (files or {}).items():
        (directory / name).write_text(contents, encoding="utf-8")
    script = f"{textwrap.dedent(code)}\nimport json\nprint({_MARKER!r} + json.dumps(result))\n"
    # -I keeps the temp directory and PYTHON* env vars off sys.path; the venv's packages still load.
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-I", "-c", script],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line for line in proc.stdout.splitlines() if line.startswith(_MARKER)]
    if proc.returncode != 0 or not lines:
        pytest.fail(f"config boot failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return Boot(
        values=json.loads(lines[-1].removeprefix(_MARKER)),
        files={path.name: _read_ini(path) for path in sorted(directory.glob("*.ini"))},
    )


@pytest.fixture
def boot_config(tmp_path: Path) -> BootConfig:
    """Boot wd-config in this test's `tmp_path`; see `BootConfig`."""

    def run(code: str, *, files: Mapping[str, str] | None = None) -> Boot:
        return boot(tmp_path, code, files=files)

    return run
