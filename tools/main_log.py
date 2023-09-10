import logging
import os
import re
import shutil
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from discord.ext import tasks

from tools.config_reader import config
from _types.bot import WinterDragon

KEEP_LATEST = config.getboolean("Main", "keep_latest_logs")

class Logs:
    bot: WinterDragon
    bot_logger: logging.Logger
    discord_logger: logging.Logger
    sql_logger: logging.Logger

    def __init__(self, bot: WinterDragon) -> None:
        self.bot = bot
        self.bot_logger = logging.getLogger(f"{config['Main']['bot_name']}")
        self.discord_logger = logging.getLogger("discord")
        self._delete_top_level_logs()
        self._add_sql_logger()
        self.setup_logging(self.bot_logger, "bot.log")
        self.setup_logging(self.discord_logger, "discord.log")
        self.bot_logger.addHandler(logging.StreamHandler())


    @classmethod
    def _add_sql_logger(cls) -> None:
        try:
            cls.sql_logger
        except AttributeError:
            from tools.database_tables import logger as sql_logger

            cls.sql_logger = sql_logger


    @tasks.loop(hours=24)
    async def daily_save_logs(self) -> None:
        self.save_logs()
        self.logging_rollover()


    @daily_save_logs.before_loop
    async def before_async_init(self) -> None:
        self.bot_logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @staticmethod
    def setup_logging(logger: logging.Logger, filename: str) -> None:
        logger.setLevel(config["Main"]["log_level"])
        handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        logger.addHandler(handler)


    def logs_size_limit_check(self, size_in_kb: int) -> bool:
        """Check if the stored logs total size in kb, is bigger then given value

        Args:
            size_in_kb (int): Size in kb

        Returns:
            bool: True, False
        """
        total_size = sum(
            os.path.getsize(os.path.join(root, file))
            for root, _, files in os.walk(config["Main"]["log_path"])
            for file in files
        )
        self.bot_logger.debug(f"{total_size=} {size_in_kb=}")
        return total_size > size_in_kb


    def delete_oldest_saved_logs(self) -> None:
        """Delete the oldest findable logs"""
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
        regex = r"(\.\/logs)(\/|\\|\d|-|_)+"

        folder_path = re.match(regex, oldest_files[0])[0]
        self.bot_logger.info(f"deleting old logs for space: {folder_path=}")

        for file in os.listdir(folder_path):
            os.remove(f"{folder_path}{file}")
        os.rmdir(folder_path)


    def save_logs(self) -> None:
        size_limit = config.getint("Main", "log_size_kb_limit")
        while self.logs_size_limit_check(size_limit):
            self.delete_oldest_saved_logs()

        log_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        os.makedirs(f"{config['Main']['log_path']}/{log_time}", exist_ok=True)

        self.bot_logger.info("Saving log files")
        self.bot_logger.info(f"Bot uptime: {datetime.now(timezone.utc) - self.bot.launch_time}")

        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                print(file)
                shutil.copy(src=f"./{file}", dst=f"{config['Main']['log_path']}/{log_time}/{file}")


    def logging_rollover(self) -> None:
        """Rolls over bot, discord and sql log handlers."""
        for handler in [
            *self.sql_logger.handlers,
            *self.discord_logger.handlers,
            *self.bot_logger.handlers,
        ]:
            if isinstance(handler, RotatingFileHandler):
                handler.doRollover()


    def delete_latest_logs(self) -> None:
        if KEEP_LATEST:
            self.bot_logger.info("Keeping top level logs.")
            return
        self._delete_top_level_logs()


    @staticmethod
    def _delete_top_level_logs() -> None:
        """Deletes the top level logs (not in logs directory)"""
        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                print(f"Removing {file}")
                os.remove(file)


    def shutdown(self) -> None:
        """Calls `save_logs` and `delete_latest_logs` before `logging.shutdown`"""
        self.save_logs()
        self.delete_latest_logs()
        logging.shutdown()