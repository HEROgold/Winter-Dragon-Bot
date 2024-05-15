# sourcery skip: dont-import-test-modules
from discord.ext import commands
from hypothesis import given
from hypothesis.strategies import text

from _types.bot import WinterDragon
from tools.config_reader import INTENTS, config


@given(text())
def test_winter_dragon(name: str) -> None:
    bot = WinterDragon(
        intents=INTENTS,
        command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]),  # type: ignore
        case_insensitive=True,
    )

    assert bot.name == name
