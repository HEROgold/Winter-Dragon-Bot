"""Unit tests: Cog.command() decorator builds a Command."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from wd_bot.commands import Command


def _load_example_cog() -> type:
    """Load ExampleCog from the fixture file using importlib."""
    spec = importlib.util.spec_from_file_location("example_cog", Path(__file__).parent / "fixtures" / "example_cog.py")
    if spec is None or spec.loader is None:
        msg = "Failed to load example_cog fixture"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ExampleCog


def test_command_decorator_produces_a_command() -> None:
    """Test that @Cog.command() decorator produces a Command instance with correct name."""
    example_cog = _load_example_cog()
    assert isinstance(example_cog.__dict__["ping_user"], Command)  # noqa: S101
    assert example_cog.__dict__["ping_user"].name == "ping-user"  # noqa: S101
