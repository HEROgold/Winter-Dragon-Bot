"""Main file for the bot."""

import asyncio
import logging
import signal
import sys
from logging.handlers import RotatingFileHandler
from threading import Thread

import aiofiles
import discord
from discord.ext import commands

from bot import WinterDragon
from bot.config import config
from bot.constants import BOT_CONFIG, INTENTS
from bot.errors.config import ConfigError
from tools.main_log import logs


# from tools.port_finder import get_v4_port
# from website.app import app


if not config.is_valid():
    msg = f"""Config is not yet updated!, update the following:
        {', '.join(config.get_invalid())}"""
    raise ConfigError(msg)


bot = WinterDragon(
    intents=INTENTS,
    command_prefix=commands.when_mentioned_or(config["Main"]["prefix"]),  # type: ignore
    case_insensitive=True,
)

tree = bot.tree
threads: list[Thread] = []


def setup_logging(logger: logging.Logger, filename: str) -> None:
    logger.setLevel(config["Main"]["log_level"])
    # handler = logging.FileHandler(filename=filename, encoding="utf-8", mode="w")
    handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)


@bot.event
async def on_ready() -> None:
    invite_link = bot.get_bot_invite()

    logs["bot"].info(f"Logged on as {bot.user}!")
    print("Bot is running!")
    print("invite link: ", invite_link)



@commands.is_owner()
@tree.command(name="shutdown", description="(For bot developer only)")
async def slash_shutdown(interaction: discord.Interaction) -> None:
    try:
        await interaction.response.send_message("Shutting down.", ephemeral=True)
        logs["bot"].info("shutdown by command.")
    except Exception:  # noqa: BLE001
        logs["bot"].exception("")
    raise KeyboardInterrupt


def terminate(*args, **kwargs) -> None:
    logs.logger.warning(f"{args=}, {kwargs=}")
    logs.logger.info("terminated")
    logs.shutdown()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.close())
    except Exception as e:  # noqa: BLE001
        print(e)

    for thread in threads:
        try:
            thread.join()
        except Exception as e:  # noqa: BLE001
            print(e)
        finally:
            del thread
    sys.exit()


async def main() -> None:
    async with bot:
        # t = Thread(
        #     target=app.run,
        #     kwargs={"host": "0.0.0.0", "port": get_v4_port(), "debug": False},
        #     daemon=True, name="flask"
        # )
        # t.start()

        invite_link = bot.get_bot_invite()
        config.set("Main", "application_id", f"{bot.application_id}")
        config.set("Main", "bot_invite", invite_link.replace("%", "%%"))

        async with aiofiles.open(BOT_CONFIG, "w") as f:
            await config.write(f, space_around_delimiters=False)

        bot.log_saver = asyncio.create_task(logs.daily_save_logs())
        await bot.load_extensions()
        await bot.start(config["Tokens"]["discord_token"])


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    asyncio.run(main())
