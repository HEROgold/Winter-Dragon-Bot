import logging
import os
import re
import shutil
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from discord.ext import commands, tasks

from tools.config_reader import config


class logs:
    bot: commands.Bot
    bot_logger: logging.Logger
    discord_logger: logging.Logger

    def __init__(self, bot: commands.bot) -> None:
        self.bot = bot
        self.bot_logger = logging.getLogger(f"{config['Main']['bot_name']}")
        self.discord_logger = logging.getLogger("discord")
        self.delete_toplevel_logs()
        self.setup_logging(self.bot_logger, "bot.log")
        self.setup_logging(self.discord_logger, "discord.log")
        self.bot_logger.addHandler(logging.StreamHandler())


    @tasks.loop(hours=24)
    async def daily_save_logs(self) -> None:
        self.save_logs()


    @daily_save_logs.before_loop
    async def before_async_init(self) -> None:
        self.bot_logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @staticmethod
    def setup_logging(logger: logging.Logger, filename: str) -> None:
        logger.setLevel(config["Main"]["log_level"])
        # handler = logging.FileHandler(filename=filename, encoding="utf-8", mode="w")
        handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        logger.addHandler(handler)


    def logs_size_limit_check(self, size_in_kb: int) -> bool:
        total_size = sum(
            os.path.getsize(os.path.join(root, file))
            for root, _, files in os.walk(config["Main"]["log_path"])
            for file in files
        )
        self.bot_logger.debug(f"{total_size=} {size_in_kb=}")
        return total_size > size_in_kb


    def delete_oldest_saved_logs(self) -> None:
        oldest_files = sorted((
                os.path.join(root, file)
                for root, _, files in os.walk(config["Main"]["log_path"])
                for file in files
            ),
            key=os.path.getctime,
        )
        # Some regex magic https://regex101.com/r/he2KNZ/1
        # "./logs\\2023-05-08-00-10-27\\bot.log" matches into
        # /logs\\2023-05-08-00-10-27\\
        regex = r"(\./logs)(/|\d|-|_)+"

        if os.name == "nt":
            folder_path = re.match(regex, oldest_files[0])
        if os.name == "posix":
            folder_path = re.search(regex, oldest_files[0])[0]
        self.bot_logger.info(f"deleting old logs for space: {folder_path=}")

        for file in os.listdir(folder_path):
            os.remove(f"{folder_path}{file}")
        os.rmdir(folder_path)


    def save_logs(self) -> None:
        while self.logs_size_limit_check(int(config["Main"]["log_size_kb_limit"])):
            self.delete_oldest_saved_logs()

        log_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        os.makedirs(f"{config['Main']['log_path']}/{log_time}", exist_ok=True)

        self.bot_logger.info("Saving log files")
        self.bot_logger.info(f"Bot uptime: {datetime.now(timezone.utc) - self.bot.launch_time}")

        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                print(file)
                shutil.copy(src=f"./{file}", dst=f"{config['Main']['log_path']}/{log_time}/{file}")
        self.logging_rollover()


    def logging_rollover(self) -> None:
        from tools.database_tables import logger as sql_logger
        log_handlers = []
        log_handlers.extend(sql_logger.handlers)
        log_handlers.extend(self.discord_logger.handlers)
        log_handlers.extend(self.bot_logger.handlers)
        for handler in log_handlers:
            if isinstance(handler, RotatingFileHandler):
                handler.doRollover()


    def delete_toplevel_logs(self) -> None:
        if config["Main"]["keep_latest_logs"] == "True":
            return
        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                print(f"Removing {file}")
                os.remove(file)


if __name__ == "__main__":
    l = logs

