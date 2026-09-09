"""Generate wd_bot/listener.pyi from wd_discord.gateway.events.EventName.

`listener.pyi` is generated, not hand-written: it holds one `@overload` of
`wd_bot.listener.listener` per modeled `EventName` member, mirroring
wd-discord/scripts/generate_dispatch_overloads.py (same underlying source data - EventName
members with `.model` set), so a cog author's handler gets its payload parameter checked
against the right type (`@Cog.listener(EventName.MESSAGE_CREATE)` requires
`def foo(self, message: Message) -> ...`, not e.g. `GuildCreate`).

Unlike dispatch.pyi's overloads, these key off the *model* only, not a payload TypedDict -
`listener()` never sees a raw payload dict, only the already-parsed model a listener receives.

Usage (from the repo root, via `uv run` - see the PEP 723 header below for how this
script gets `wd_discord` importable without being part of the main project env):

    uv run wd-bot/scripts/generate_listener_overloads.py           # regenerate listener.pyi
    uv run wd-bot/scripts/generate_listener_overloads.py --check   # verify it's up to date (CI/pre-push)
"""
# /// script
# requires-python = ">=3.15"
# dependencies = [
#     "wd-discord",
# ]
#
# [tool.uv.sources]
# wd-discord = { path = "../../wd-discord", editable = true }
# ///

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from wd_discord.gateway.events import EventName

SCRIPT_PATH = Path(__file__).resolve()
OUTPUT_PATH = SCRIPT_PATH.parents[1] / "src" / "wd_bot" / "listener.pyi"

_HEADER_TEMPLATE = """\
# Typed @overload signatures for wd_bot.listener.listener.
#
# GENERATED FILE - do not hand-edit. Regenerate with:
#
#     uv run wd-bot/scripts/generate_listener_overloads.py
#
# One overload per EventName member that has a model wired up (EventName.X.model is not None) -
# mirrors wd-discord/scripts/generate_dispatch_overloads.py's dispatch.pyi (same source data).
# Members without a model fall through to the general bare-name overload below.
# (no module docstring here on purpose - ruff's PYI021 flags docstrings in stub files)

from collections.abc import Awaitable, Callable
from typing import Any, Literal, overload

from wd_discord.gateway import {events_import}

type _BoundHandler[T] = Callable[[Any, T], Awaitable[None]]

"""

_FOOTER = """
@overload
def listener[F: Callable[..., Awaitable[None]]](name: str | None = ...) -> Callable[[F], F]: ...
"""


def render() -> str:
    """Render listener.pyi's full source (unformatted - the caller runs ruff format on it)."""
    overload_lines: list[str] = []
    referenced_names: set[str] = set()
    for member in EventName:
        if member.model is None:
            continue
        model = member.model.__name__
        referenced_names.add(model)
        overload_lines.append("@overload")
        overload_lines.append(
            f"def listener(name: Literal[EventName.{member.name}]) -> "
            f"Callable[[_BoundHandler[{model}]], _BoundHandler[{model}]]: ...",
        )

    events_import = ", ".join(["EventName", *sorted(referenced_names)])
    header = _HEADER_TEMPLATE.format(events_import=events_import)
    return header + "\n".join(overload_lines) + _FOOTER


def _ruff_format(path: Path) -> None:
    subprocess.run(["uv", "run", "ruff", "format", str(path)], check=True, cwd=SCRIPT_PATH.parents[1])  # noqa: S603, S607


def generate() -> None:
    """Write listener.pyi, then run ruff format on it to match the repo's style."""
    OUTPUT_PATH.write_text(render(), encoding="utf-8")
    _ruff_format(OUTPUT_PATH)


def check() -> bool:
    """Return True if the checked-in listener.pyi matches what generate() would produce."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        candidate = Path(tmp_dir) / "listener.pyi"
        candidate.write_text(render(), encoding="utf-8")
        _ruff_format(candidate)
        if not OUTPUT_PATH.exists():
            print(f"{OUTPUT_PATH} does not exist - run without --check to generate it.")  # noqa: T201
            return False
        current = OUTPUT_PATH.read_text(encoding="utf-8")
        expected = candidate.read_text(encoding="utf-8")
        if current == expected:
            return True
        print(f"{OUTPUT_PATH} is out of date - run without --check to regenerate it.")  # noqa: T201
        return False


def main() -> None:
    """Parse CLI args and run generate() or check() accordingly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify listener.pyi is up to date; don't write it")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check() else 1)
    generate()


if __name__ == "__main__":
    main()
