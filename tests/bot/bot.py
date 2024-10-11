# sourcery skip: dont-import-test-modules
from discord.ext import commands
from hypothesis import given
from hypothesis.strategies import text

from bot import WinterDragon
from bot.config import config
from bot.constants import INTENTS


@given(text())
def test_winter_dragon() -> None:
    WinterDragon(
        intents=INTENTS,
        command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]),  
        case_insensitive=True,
    )
