"""Unit tests: Bot's command registry, INTERACTION_CREATE dispatch and startup sync (no real Discord calls)."""

from __future__ import annotations

import asyncio
import types
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from wd_bot.auto_sync import DefaultCommandSyncer
from wd_bot.bot import Bot
from wd_bot.cogs import Cog, GroupCog
from wd_bot.commands import CommandGroup
from wd_discord.gateway import EventName
from wd_discord.gateway.events import Interaction, InteractionDataOption


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence

    import pytest
    from conftest import InteractionFactory
    from wd_bot.commands import Command


CALLS: list[Interaction] = []


class _PingCog(Cog, auto_load=False):
    @Cog.command(name="ping", description="d")
    async def ping(self, interaction: Interaction) -> None:
        CALLS.append(interaction)


class _SubPingCog(_PingCog, auto_load=False):
    """Inherits the command from a parent class."""


class _AutoPingCog(Cog):
    """Auto-loading cog (the default), as real extension cogs are."""

    @Cog.command(name="auto-ping", description="d")
    async def auto_ping(self, interaction: Interaction) -> None:
        CALLS.append(interaction)


def _make_bot() -> Bot:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    return bot





async def test_add_cog_registers_commands() -> None:
    bot = _make_bot()
    cog = _PingCog(bot=bot)
    await bot.add_cog(cog)
    assert "ping" in bot._commands


async def test_add_cog_registers_inherited_commands() -> None:
    bot = _make_bot()
    cog = _SubPingCog(bot=bot)
    await bot.add_cog(cog)
    assert bot._commands["ping"][0] is cog


class _OtherPingCog(Cog, auto_load=False):
    @Cog.command(name="ping", description="d")
    async def ping(self, interaction: Interaction) -> None:
        CALLS.append(interaction)


async def test_add_cog_warns_on_duplicate_command_name(capsys: pytest.CaptureFixture[str]) -> None:
    bot = _make_bot()
    await bot.add_cog(_PingCog(bot=bot))
    other = _OtherPingCog(bot=bot)
    await bot.add_cog(other)
    assert bot._commands["ping"][0] is other
    assert "Duplicate command 'ping'" in capsys.readouterr().err


async def test_dispatch_interaction_invokes_matching_command(make_interaction: InteractionFactory) -> None:
    CALLS.clear()
    bot = _make_bot()
    await bot.add_cog(_PingCog(bot=bot))
    interaction = make_interaction("ping")
    await bot._dispatch_interaction(interaction)
    assert [interaction] == CALLS


async def test_dispatch_interaction_is_registered_as_listener() -> None:
    bot = _make_bot()
    assert bot._dispatch_interaction in bot._listeners[EventName.INTERACTION_CREATE.value]


async def test_dispatch_unknown_command_is_ignored(make_interaction: InteractionFactory) -> None:
    CALLS.clear()
    bot = _make_bot()
    await bot._dispatch_interaction(make_interaction("nope"))
    assert CALLS == []


async def test_init_cogs_registers_commands_before_any_other_await() -> None:
    bot = _make_bot()
    module = types.ModuleType("fake_ext")
    module._AutoPingCog = _AutoPingCog  # noqa: SLF001
    module.Cog = Cog
    # _init_cogs must not rely on the scheduled auto_load task: the registry is filled on return.
    await bot._init_cogs(module)
    assert "auto-ping" in bot._commands


class _FakeSyncer:
    def __init__(self) -> None:
        self.calls: list[tuple[object, list[Command]]] = []
        self.allow_deletes: bool | None = None

    async def sync(self, client: object, commands: Sequence[Command], *, allow_deletes: bool = True) -> None:
        self.calls.append((client, list(commands)))
        self.allow_deletes = allow_deletes


async def test_syncer_defaults_and_can_be_swapped() -> None:
    bot = _make_bot()
    assert isinstance(bot.syncer, DefaultCommandSyncer)
    fake = _FakeSyncer()
    bot.syncer = fake
    assert bot.syncer is fake


async def test_sync_commands_delegates_to_syncer() -> None:
    bot = _make_bot()
    fake = _FakeSyncer()
    bot.syncer = fake
    await bot.add_cog(_PingCog(bot=bot))
    client = object()
    await bot.sync_commands(client)  # type: ignore[arg-type]
    assert len(fake.calls) == 1
    assert fake.calls[0][0] is client
    assert [c.name for c in fake.calls[0][1]] == ["ping"]


async def test_sync_commands_allows_deletes_by_default() -> None:
    bot = _make_bot()
    fake = _FakeSyncer()
    bot.syncer = fake
    await bot.sync_commands(object())  # type: ignore[arg-type]
    assert fake.allow_deletes is True


async def test_failed_extension_disables_deletes() -> None:
    bot = _make_bot()
    fake = _FakeSyncer()
    bot.syncer = fake
    bot.load_extension = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

    async def one_extension() -> AsyncGenerator[str]:
        yield "broken"

    bot.get_extensions = one_extension  # type: ignore[method-assign]
    await bot.load_extensions()
    await bot.sync_commands(object())  # type: ignore[arg-type]
    assert fake.allow_deletes is False
    assert bot._failed_extensions == {"broken"}


async def test_successful_load_clears_failed_extension() -> None:
    bot = _make_bot()
    bot._failed_extensions.add("commands")
    bot.extensions_package = types.ModuleType("wd_bot")
    bot._load_from_module_spec = AsyncMock()  # type: ignore[method-assign]
    await bot.load_extension("commands")
    assert "commands" not in bot._failed_extensions


class _BrokenSyncer:
    async def sync(self, client: object, commands: Sequence[Command], *, allow_deletes: bool = True) -> None:  # noqa: ARG002
        msg = "database is down"
        raise RuntimeError(msg)


async def test_startup_sync_logs_failure_instead_of_raising(capsys: pytest.CaptureFixture[str]) -> None:
    bot = _make_bot()
    bot.syncer = _BrokenSyncer()
    await bot._startup_sync(object())  # type: ignore[arg-type]
    err = capsys.readouterr().err
    assert "Startup command sync failed" in err
    assert "database is down" in err


async def test_discovery_failure_disables_deletes() -> None:
    bot = _make_bot()
    fake = _FakeSyncer()
    bot.syncer = fake
    bot.extensions_package = types.ModuleType("no_path_package")  # no __path__: discovery raises
    await bot.load_extensions()
    await bot.sync_commands(object())  # type: ignore[arg-type]
    assert fake.allow_deletes is False
    assert bot._failed_extensions == {"no_path_package"}


class _BoomCog(Cog, auto_load=False):
    @Cog.command(name="boom", description="d")
    async def boom(self, interaction: Interaction) -> None:  # noqa: ARG002
        msg = "handler broke"
        raise RuntimeError(msg)


async def test_dispatch_sends_ephemeral_error_when_handler_raises(make_interaction: InteractionFactory) -> None:
    bot = _make_bot()
    respond = AsyncMock()
    bot.client = types.SimpleNamespace(create_interaction_response=respond)  # type: ignore[assignment]
    await bot.add_cog(_BoomCog(bot=bot))
    interaction = make_interaction("boom")

    await bot._dispatch_interaction(interaction)

    respond.assert_awaited_once_with(interaction, content="Something went wrong running this command.", ephemeral=True)


async def test_dispatch_sends_no_error_reply_on_success(make_interaction: InteractionFactory) -> None:
    bot = _make_bot()
    respond = AsyncMock()
    bot.client = types.SimpleNamespace(create_interaction_response=respond)  # type: ignore[assignment]
    await bot.add_cog(_PingCog(bot=bot))

    await bot._dispatch_interaction(make_interaction("ping"))

    respond.assert_not_awaited()


class _AdminTools(GroupCog, auto_load=False):
    """Admin tools."""

    @Cog.command(name="ping", description="d")
    async def ping(self, interaction: Interaction) -> None:
        CALLS.append(interaction)


async def test_group_cog_registers_one_group_and_dispatches_subcommands(make_interaction: InteractionFactory) -> None:
    CALLS.clear()
    bot = _make_bot()
    cog = _AdminTools(bot=bot)
    await bot.add_cog(cog)

    group = bot._commands["admin-tools"][1]
    assert isinstance(group, CommandGroup)
    assert group.description == "Admin tools."
    assert list(group.subcommands) == ["ping"]
    assert "ping" not in bot._commands

    interaction = make_interaction("admin-tools")
    assert interaction.data is not None
    interaction.data.options = [InteractionDataOption(name="ping", type=1)]
    await bot._dispatch_interaction(interaction)
    assert CALLS == [interaction]
