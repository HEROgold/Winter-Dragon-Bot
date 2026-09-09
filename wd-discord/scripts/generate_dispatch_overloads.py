"""Generate wd_discord/gateway/dispatch.pyi from wd_discord.gateway.events.EventName.

`dispatch.pyi` is generated, not hand-written: it holds one `@overload` of
`parse_dispatch` per `EventName` member, and hand-maintaining ~75 near-identical
overloads is exactly the kind of thing that silently drifts out of sync with the
enum it's supposed to describe. This script is the single source of truth for how
an event name maps to its payload/model type names; `dispatch.pyi` is its output.

Usage (from the repo root, via `uv run` - see the PEP 723 header below for how this
script gets `wd_discord` importable without being part of the main project env):

    uv run wd-discord/scripts/generate_dispatch_overloads.py           # regenerate dispatch.pyi
    uv run wd-discord/scripts/generate_dispatch_overloads.py --check   # verify it's up to date (CI/pre-push)

Naming convention: an event's model is the PascalCase of its name (MESSAGE_UPDATE ->
MessageUpdate), and its payload TypedDict is that name + "Payload" regardless (always
PascalCase(event name) + "Payload", e.g. MessageCreatePayload). MESSAGE_CREATE's model is
the one exception - Message predates this convention, not MessageCreate - see
_MODEL_NAME_OVERRIDES (which only ever overrides the model name, never the payload name).
Most of the generated names don't exist yet (see dispatch.pyi's own header) - that's
expected: building a real model for an event is "add its classes to events.py, then
regenerate" - this script's naming convention already points at where they should land.
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

# Events whose model doesn't follow the plain PascalCase(name) convention.
_MODEL_NAME_OVERRIDES: dict[str, str] = {
    "MESSAGE_CREATE": "Message",
}

_HEADER = '''\
"""Typed @overload signatures for wd_discord.gateway.dispatch.parse_dispatch.

GENERATED FILE - do not hand-edit. Regenerate with:

    uv run wd-discord/scripts/generate_dispatch_overloads.py

One overload per wd_discord.gateway.events.EventName member, mapping its literal name to
its payload TypedDict and model DiscordModel type by the PascalCase(event name) convention
(see generate_dispatch_overloads.py's _MODEL_NAME_OVERRIDES for the one exception). Most of the referenced
Payload/Model names below don't exist yet as real classes in events.py - that's a visible
TODO (an unresolved-name error from the type checker), not a bug in this file: build the
pair in events.py, then regenerate to pick it up.
"""

from collections.abc import Mapping
from typing import Literal, overload

from wd_discord.models import DiscordModel

from .events import EventName, GuildCreate, GuildCreatePayload, Message, MessageCreatePayload, RawEvent

'''

_FOOTER = """
@overload
def parse_dispatch(name: str, data: Mapping[str, object]) -> DiscordModel: ...
"""


def _pascal_case(event_name: str) -> str:
    return "".join(word.capitalize() for word in event_name.split("_"))


def model_name_for(event_name: str) -> str:
    """Return the DiscordModel class name an event's overload should reference."""
    return _MODEL_NAME_OVERRIDES.get(event_name, _pascal_case(event_name))


def payload_name_for(event_name: str) -> str:
    """Return the payload TypedDict name an event's overload should reference.

    Always PascalCase(event_name) + "Payload" - independent of _MODEL_NAME_OVERRIDES, which
    only overrides the *model* name (MESSAGE_CREATE's payload is MessageCreatePayload even
    though its model is Message, not MessageCreate).
    """
    return f"{_pascal_case(event_name)}Payload"


def render() -> str:
    """Render dispatch.pyi's full source (unformatted - the caller runs ruff format on it)."""
    lines = [_HEADER]
    for member in EventName:
        payload = payload_name_for(member.name)
        model = model_name_for(member.name)
        lines.append("@overload")
        lines.append(f"def parse_dispatch(name: Literal[EventName.{member.name}], data: {payload}) -> {model}: ...")
    lines.append(_FOOTER)
    return "\n".join(lines)


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
