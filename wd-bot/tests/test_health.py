"""Unit tests: the container health checks and the cog that keeps the bot's alive file fresh."""

import asyncio
import os
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from wd_bot.bot import Bot
from wd_bot.testing import detached_cog

import winter_dragon.cogs.health as health_cog
from winter_dragon import health
from winter_dragon.cogs.health import Health


if TYPE_CHECKING:
    from pathlib import Path

    from wd_discord.gateway.sharding import ShardManager


@pytest.fixture
def alive_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "winter-dragon-alive"
    monkeypatch.setattr(health, "ALIVE_FILE", path)
    monkeypatch.setattr(health_cog, "ALIVE_FILE", path)
    return path


def test_the_bot_is_unhealthy_without_an_alive_file(alive_file: Path) -> None:
    assert not alive_file.exists()
    assert not health.bot_healthy()


def test_the_bot_is_healthy_while_the_alive_file_is_fresh(alive_file: Path) -> None:
    alive_file.touch()
    assert health.bot_healthy()


def test_the_bot_is_unhealthy_once_the_alive_file_is_stale(alive_file: Path) -> None:
    alive_file.touch()
    stale = time.time() - health.ALIVE_MAX_AGE - 1
    os.utime(alive_file, (stale, stale))
    assert not health.bot_healthy()


def test_the_web_check_fails_when_nothing_listens(monkeypatch: pytest.MonkeyPatch) -> None:
    from winter_dragon.web.settings import DashboardSettings  # noqa: PLC0415

    monkeypatch.setattr(DashboardSettings, "port", 1)
    assert not health.web_healthy()


@pytest.mark.parametrize("argv", [[], ["db"], ["bot", "web"]])
def test_main_rejects_anything_but_one_known_check(argv: list[str]) -> None:
    assert health.main(argv) == 2  # noqa: PLR2004 - usage error


def test_main_exits_with_the_checks_result(alive_file: Path) -> None:
    assert health.main(["bot"]) == 1
    alive_file.touch()
    assert health.main(["bot"]) == 0


async def test_the_cog_touches_the_alive_file_while_every_shard_is_alive(alive_file: Path) -> None:
    cog = detached_cog(Health, shard_manager=SimpleNamespace(alive=True))
    await cog.touch_alive_file()
    assert alive_file.exists()


@pytest.mark.parametrize("manager", [None, SimpleNamespace(alive=False)])
async def test_the_cog_leaves_the_alive_file_alone_while_the_bot_is_not_connected(
    alive_file: Path,
    manager: SimpleNamespace | None,
) -> None:
    cog = detached_cog(Health, shard_manager=manager)
    await cog.touch_alive_file()
    assert not alive_file.exists()


async def test_a_loaded_cog_keeps_touching_the_file_until_it_is_unloaded(alive_file: Path) -> None:
    bot = Bot()
    bot.loop = asyncio.get_running_loop()
    bot.shard_manager = cast("ShardManager", SimpleNamespace(alive=True))
    cog = Health(bot=bot)

    await bot.add_cog(cog)
    await asyncio.sleep(0)
    assert alive_file.exists()

    await bot.remove_cog(cog)
    alive_file.unlink()
    await asyncio.sleep(0)
    assert not alive_file.exists()
