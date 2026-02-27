"""Main file for the bot."""

import asyncio
import signal
import sys
from typing import TYPE_CHECKING, Any

from discord.ext import commands
from herogold.orm.constants import engine
from herogold.orm.model import BaseModel

from winter_dragon.bot.core.bot import INTENTS, WinterDragon
from winter_dragon.bot.core.sentry import Sentry
from winter_dragon.bot.core.settings import Settings
from winter_dragon.config import Config, ConfigError, Environments, GlobalSettings, config


if TYPE_CHECKING:
    import discord


if not config.is_valid():
    msg = f"""Config is not yet updated!, update the following:
        {", ".join(config.get_invalid())}"""
    raise ConfigError(msg)


bot = WinterDragon(
    intents=INTENTS,
    command_prefix=commands.when_mentioned_or(Settings.prefix),
    case_insensitive=True,
)
tree = bot.tree


@bot.event
async def on_ready() -> None:
    """Log when the bot is ready. Note that this may happen multiple times per boot."""
    invite_link = bot.get_bot_invite()
    # setting values requires an instance.
    settings = Settings()
    settings.application_id = bot.application_id
    settings.bot_invite = invite_link.replace("%", "%%")
    Config.write()

    bot.logger.info(f"Logged on as {bot.user}!")


@commands.is_owner()
@tree.command(name="shutdown", description="(For bot developer only)")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    """Shutdown the bot."""
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        bot.logger.info("shutdown by command.")
        await bot.close()
        terminate()
    except Exception:
        bot.logger.exception("")


def terminate(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401 Catch all arguments to log before termination.
    """Terminate the bot."""
    bot.logger.warning(f"{args=}, {kwargs=}")
    bot.logger.info("terminated")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.close())
    except Exception:  # noqa: BLE001, S110
        pass
    sys.exit()


async def main() -> None:
    """Entrypoint of the program."""
    async with bot:
        BaseModel.metadata.create_all(engine, checkfirst=True)
        await bot.load_extensions()
        await bot.start()


# Enable debugpy for remote debugging in development
if GlobalSettings.environment == Environments.development:
    try:
        import debugpy  # pyright: ignore[reportMissingImports] # noqa: T100  # ty:ignore[unresolved-import]

        debugpy.listen(("0.0.0.0", 5679))  # noqa: S104, T100
        print("debugpy listening on 0.0.0.0:5679")  # noqa: T201
    except ImportError:
        print("debugpy not installed; skipping remote debug setup.")  # noqa: T201


if __name__ == "__main__":
    Sentry()
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
