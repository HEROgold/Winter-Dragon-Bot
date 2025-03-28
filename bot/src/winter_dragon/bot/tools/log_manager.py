import asyncio
import logging
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from winter_dragon.bot.config import Config, config


KEEP_LATEST = config.getboolean("Main", "keep_latest_logs")


class LogsManager:
    first_rollover: bool = False

    @Config.default("Main", "log_path", "./logs")
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
        log_level = config.get("Main", "log_level")
        logger.setLevel(log_level)
        handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        logger.addHandler(handler)

    @property
    def log_path(self) -> str:
        """Get the log path from the config."""
        return config.get("Main", "log_path")


    def logs_size_limit_check(self, size_in_kb: int) -> bool:
        """Check if the stored logs total size in kb, is bigger then given value.

        Args:
        ----
            size_in_kb (int): Size in kb

        Returns:
        -------
            bool: True, False

        """
        total_size = sum(
            (Path(root) / file).stat().st_size
            for root, _, files in os.walk(self.log_path)
            for file in files
        )
        self.logger.debug(f"{total_size=} {size_in_kb=}")
        return total_size > size_in_kb


    def delete_oldest_saved_logs(self) -> None:
        """Delete the oldest findable logs."""
        oldest_files = sorted((
            Path(root) / file
            for root, _, files in os.walk(self.log_path)
            for file in files
            ),
            key=os.path.getctime,
        )
        # Some regex magic https://regex101.com/r/he2KNZ/1
        # "./logs\\2023-05-08-00-10-27\\bot.log" matches into
        # /logs\\2023-05-08-00-10-27\\
        regex = r"(\.\/logs)(\/|\\|\d|-|_)+"

        folder_path = re.match(regex, str(oldest_files[0]))[0]
        self.logger.info(f"deleting old logs for space: {folder_path=}")

        for file in os.listdir(folder_path):
            Path(f"{folder_path}{file}").unlink()
        Path(folder_path).rmdir()

    @Config.default("Main", "log_size_kb_limit", 9000000)
    def save_logs(self) -> None:
        size_limit = config.getint("Main", "log_size_kb_limit")
        while self.logs_size_limit_check(size_limit):
            self.delete_oldest_saved_logs()

        log_time = datetime.now(tz=UTC).strftime("%Y-%m-%d-%H-%M-%S")

        Path(f"{config['Main']['log_path']}/{log_time}").mkdir(parents=True, exist_ok=True)

        self.logger.info("Saving log files")
        self.logger.info(f"uptime: {datetime.now(UTC) - self.launch_time}")

        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
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
        """Delete the top level logs (not in logs directory)."""
        for file in os.listdir("./"):
            if file.endswith(".log") or file[:-2].endswith(".log"):
                self.logger.info(f"Removing {file}")
                try:
                    Path(file).unlink()
                except Exception:
                    self.logger.exception(f"Error removing file {file}")


    def shutdown(self) -> None:
        """Call `save_logs` and `delete_latest_logs` before `logging.shutdown`."""
        self.save_logs()
        self.delete_latest_logs()
        logging.shutdown()
