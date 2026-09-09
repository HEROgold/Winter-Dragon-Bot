"""Unit tests: Cog registration and gateway-event dispatch wiring (no real gateway/socket)."""

from __future__ import annotations

lazy import asyncio
lazy import sys
lazy import types
lazy from pathlib import Path

lazy import pytest
lazy from sqlmodel import create_engine
lazy from wd_bot.bot import Bot
lazy from wd_discord.gateway import Message

lazy from .fixtures.example_cog import ExampleCog


@pytest.fixture(autouse=True)
def _sqlite_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out wd_db.constants.engine with an in-memory sqlite engine.

    wd_db.constants eagerly creates a real Postgres engine at import time, which needs
    psycopg2 (not installed in this dev environment) - orthogonal to what these tests
    exercise, since Cog construction just needs *a* Session, not a real database. The stub
    is installed in sys.modules before Cog.__init__ ever touches the (lazily-imported)
    `engine` name, so the real wd_db.constants module body never executes.
    """
    stub = types.ModuleType("wd_db.constants")
    stub.engine = create_engine("sqlite://")
    monkeypatch.setitem(sys.modules, "wd_db.constants", stub)


def _message(content: str) -> Message:
    return Message(
        id="1",
        channel_id="2",
        author={"id": "3", "username": "bot", "discriminator": "0"},
        content=content,
        timestamp="t",
        tts=False,
        mention_everyone=False,
    )


async def _bot_with_running_loop() -> Bot:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    return bot


async def test_add_cog_registers_listener_and_dispatch_invokes_it() -> None:
    bot = await _bot_with_running_loop()
    cog = ExampleCog(bot=bot)
    await bot.add_cog(
        cog
    )  # deterministic registration; the auto_load task cog.__init__ scheduled is a redundant no-op (see auto_load's already-loaded guard)

    assert cog.__cog_name__ in bot.cogs
    await bot._dispatch("MESSAGE_CREATE", _message("hi"))  # noqa: SLF001 - exercising internal dispatch
    await asyncio.sleep(0)  # let the create_task'd listener (and the scheduled auto_load) run

    assert len(cog.received) == 1
    received = cog.received[0]
    assert isinstance(received, Message)
    assert received.content == "hi"


async def test_dispatch_ignores_events_with_no_listeners() -> None:
    bot = await _bot_with_running_loop()
    cog = ExampleCog(bot=bot)
    await bot.add_cog(cog)

    await bot._dispatch("MESSAGE_UPDATE", _message("irrelevant"))  # noqa: SLF001 - exercising internal dispatch
    await asyncio.sleep(0)

    assert cog.received == []


async def test_load_from_module_spec_instantiates_cogs() -> None:
    bot = await _bot_with_running_loop()
    fixture_path = Path(__file__).parent / "fixtures" / "example_cog.py"
    spec = __import__("importlib.util", fromlist=["spec_from_file_location"]).spec_from_file_location(
        "example_cog_via_spec",
        fixture_path,
    )
    assert spec is not None

    await bot._load_from_module_spec(spec, "example_cog_via_spec")  # noqa: SLF001 - exercising internal loader
    await asyncio.sleep(0)  # let the auto_load task that Cog.__init__ scheduled actually run

    assert "example_cog_via_spec" in bot._extensions  # noqa: SLF001 - test assertion
    assert "ExampleCog" in bot.cogs
