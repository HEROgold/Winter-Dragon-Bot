import asyncio
import logging
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler

from bot.config import config


KEEP_LATEST = config.getboolean("Main", "keep_latest_logs")

class Logs:
    first_rollover: bool = False

    def __init__(self) -> None:
        self._loggers: dict[str, logging.Logger] = {}
        self.launch_time = datetime.now(UTC)
        self.logger = logging.getLogger("logs")
        self._delete_top_level_logs()
        self.add_logger("logs", self.logger)
        self.logger.addHandler(logging.StreamHandler())

    def add_logger(self, name: str, logger: logging.Logger) -> None:
        self._loggers[name] = logger
        self.setup_logging(logger, f"{name}.log")

    def __getitem__(self, name: str) -> logging.Logger:
        return self._loggers[name]

    async def daily_save_logs(self) -> None:
        while True:
            if not self.first_rollover:
                self.first_rollover = True
                self.logger.info("Skipping first rollover")
                return
            if self.launch_time < datetime.now(UTC) + timedelta(hours=1):
                return
            self.logger.debug("Daily saving of logs.")
            self.save_logs()
            self.logging_rollover()
            self._delete_top_level_logs()
            await asyncio.sleep(86400)

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
        self.logger.debug(f"{total_size=} {size_in_kb=}")
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
        self.logger.info(f"deleting old logs for space: {folder_path=}")

        for file in os.listdir(folder_path):
            os.remove(f"{folder_path}{file}")
        os.rmdir(folder_path)


    def save_logs(self) -> None:
        size_limit = config.getint("Main", "log_size_kb_limit")
        while self.logs_size_limit_check(size_limit):
            self.delete_oldest_saved_logs()

        log_time = datetime.now(tz=UTC).strftime("%Y-%m-%d-%H-%M-%S")

        os.makedirs(f"{config['Main']['log_path']}/{log_time}", exist_ok=True)

        self.logger.info("Saving log files")
        self.logger.info(f"uptime: {datetime.now(UTC) - self.launch_time}")

        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                print(file)
                shutil.copy(src=f"./{file}", dst=f"{config['Main']['log_path']}/{log_time}/{file}")


    def logging_rollover(self) -> None:
        """Rollover all RotatingFileHandlers, for all loggers contained."""
        for logger in self._loggers.values():
            for handler in logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    handler.doRollover()

    def delete_latest_logs(self) -> None:
        if KEEP_LATEST:
            self.logger.info("Keeping top level logs.")
            return
        self._delete_top_level_logs()


    def _delete_top_level_logs(self) -> None:
        """Deletes the top level logs (not in logs directory)"""
        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                self.logger.info(f"Removing {file}")
                try:
                    os.remove(file)
                except Exception:
                    self.logger.exception(f"Error removing file {file}")


    def shutdown(self) -> None:
        """Calls `save_logs` and `delete_latest_logs` before `logging.shutdown`"""
        self.save_logs()
        self.delete_latest_logs()
        logging.shutdown()


bot_logger = logging.getLogger(f"{config['Main']['bot_name']}")
sql_logger = logging.getLogger("sqlalchemy.engine")
discord_logger = logging.getLogger("discord")
flask_logger = logging.getLogger("werkzeug")

logs = Logs()

logs.add_logger("bot", bot_logger)
logs.add_logger("discord", discord_logger)
logs.add_logger("flask", flask_logger)
logs.add_logger("sqlalchemy", sql_logger)

