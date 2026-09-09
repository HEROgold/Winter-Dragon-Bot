"""Generate wd_discord/gateway/dispatch.pyi from wd_discord.gateway.events.EventName.

`dispatch.pyi` is generated, not hand-written: it holds one `@overload` of `parse_dispatch`
per modeled `EventName` member, and hand-maintaining that list is exactly the kind of thing
that silently drifts out of sync with the enum it's supposed to describe. This script is the
single source of truth for how a modeled event maps to its payload/model type names;
`dispatch.pyi` is its output.

Usage (from the repo root, via `uv run` - see the PEP 723 header below for how this
script gets `wd_discord` importable without being part of the main project env):

    uv run wd-discord/scripts/generate_dispatch_overloads.py           # regenerate dispatch.pyi
    uv run wd-discord/scripts/generate_dispatch_overloads.py --check   # verify it's up to date (CI/pre-push)

Only members with `EventName.X.model is not None` get an overload - RawEvent-only events
(most of them, today) have nothing precise to say yet, and fall through to the general
`(name: str, data: Mapping[str, object]) -> DiscordModel` overload already. A member's model
name comes straight from `member.model.__name__` (the real class, no guessing); its payload
TypedDict name is assumed to be `PascalCase(event name) + "Payload"` (e.g. MessageCreatePayload
for MESSAGE_CREATE) since payload TypedDicts aren't attached to EventName the way models are -
give an event's payload TypedDict that name in events.py and this convention finds it.
"""
# /// script
# requires-python = ">=3.15"
# dependencies = [
#     "wd-discord",
# ]
#
# [tool.uv.sources]
# wd-discord = { path = "../", editable = true }
# ///

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from wd_discord.gateway.events import EventName


SCRIPT_PATH = Path(__file__).resolve()
OUTPUT_PATH = SCRIPT_PATH.parents[1] / "src" / "wd_discord" / "gateway" / "dispatch.pyi"

_HEADER_TEMPLATE = """\
# Typed @overload signatures for wd_discord.gateway.dispatch.parse_dispatch.
#
# GENERATED FILE - do not hand-edit. Regenerate with:
#
#     uv run wd-discord/scripts/generate_dispatch_overloads.py
#
# One overload per EventName member that has a model wired up (EventName.X.model is not None) -
# see generate_dispatch_overloads.py for the naming convention and why members without a model
# aren't listed here individually (they already resolve fine through the general fallback below).
# (no module docstring here on purpose - ruff's PYI021 flags docstrings in stub files)

from collections.abc import Mapping
from typing import Literal, overload

from wd_discord.models import DiscordModel

from .events import {events_import}

"""

_FOOTER = """
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
"""


def _pascal_case(event_name: str) -> str:
    return "".join(word.capitalize() for word in event_name.split("_"))


def payload_name_for(event_name: str) -> str:
    """Return the payload TypedDict name a modeled event's overload should reference.

    Always PascalCase(event_name) + "Payload" (e.g. MessageCreatePayload for MESSAGE_CREATE) -
    payload TypedDicts aren't attached to EventName members the way models are, so this is a
    naming convention rather than something read off the member itself.
    """
    return f"{_pascal_case(event_name)}Payload"


def render() -> str:
    """Render dispatch.pyi's full source (unformatted - the caller runs ruff format on it)."""
    overload_lines: list[str] = []
    referenced_names: set[str] = set()
    for member in EventName:
        if member.model is None:
            continue
        payload = payload_name_for(member.name)
        model = member.model.__name__
        referenced_names.add(payload)
        referenced_names.add(model)
        overload_lines.append("@overload")
        overload_lines.append(f"def parse_dispatch(name: Literal[EventName.{member.name}], data: {payload}) -> {model}: ...")

    events_import = ", ".join(["EventName", *sorted(referenced_names)])
    header = _HEADER_TEMPLATE.format(events_import=events_import)
    return header + "\n".join(overload_lines) + _FOOTER


def _ruff_format(path: Path) -> None:
    subprocess.run(["uv", "run", "ruff", "format", str(path)], check=True, cwd=SCRIPT_PATH.parents[1])  # noqa: S603, S607


def generate() -> None:
    """Write dispatch.pyi, then run ruff format on it to match the repo's style."""
    OUTPUT_PATH.write_text(render(), encoding="utf-8")
    _ruff_format(OUTPUT_PATH)


def check() -> bool:
    """Return True if the checked-in dispatch.pyi matches what generate() would produce."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        candidate = Path(tmp_dir) / "dispatch.pyi"
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
    parser.add_argument("--check", action="store_true", help="verify dispatch.pyi is up to date; don't write it")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check() else 1)
    generate()


if __name__ == "__main__":
    main()
