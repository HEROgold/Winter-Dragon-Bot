"""Manage logs for the bot."""
import logging
import os
import re
import shutil
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from winter_dragon.bot.config import Config
from winter_dragon.bot.settings import Settings


class LogsManager:
    """Manages some loggers and their log files."""

    current_directory = Path("./")
    keep_latest = Config(default=False)
    log_path = Config("./logs")
    log_size_kb_limit = Config(9000000)

    def __init__(self) -> None:
        """Initialize the LogsManager."""
        self._loggers: dict[str, logging.Logger] = {}
        self.launch_time = datetime.now(UTC)
        self.logger = logging.getLogger("logs")
        self._delete_top_level_logs()
        self.add_logger("logs", self.logger)
        self.logger.addHandler(logging.StreamHandler())

    def add_logger(self, name: str, logger: logging.Logger) -> None:
        """Add a logger to the manager."""
        self._loggers[name] = logger
        self.setup_logging(logger, f"{name}.log")

    def __getitem__(self, name: str) -> logging.Logger:
        """Get the logger by name."""
        return self._loggers[name]

    @staticmethod
    def setup_logging(logger: logging.Logger, filename: str) -> None:
        """Set up logging for the given logger."""
        logger.setLevel(Settings.log_level)
        handler = RotatingFileHandler(filename=filename, backupCount=7, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        logger.addHandler(handler)

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

        match = re.match(regex, str(oldest_files[0]))
        if not match:
            self.logger.warning("No match found for saving log files.")
            return
        folder_path = match[0]
        self.logger.info(f"deleting old logs for space: {folder_path=}")

        for file in Path(folder_path).iterdir():
            file.unlink()
        Path(folder_path).rmdir()

    def save_logs(self) -> None:
        """Save logs to a new directory."""
        while self.logs_size_limit_check(self.log_size_kb_limit):
            self.delete_oldest_saved_logs()

        log_time = datetime.now(tz=UTC).strftime("%Y-%m-%d-%H-%M-%S")

        Path(f"{self.log_path}/{log_time}").mkdir(parents=True, exist_ok=True)

        self.logger.info("Saving log files")
        self.logger.info(f"uptime: {datetime.now(UTC) - self.launch_time}")

        for file in self.current_directory.iterdir():
            if file.name.endswith(".log") or file.name[:-2].endswith(".log"):
                shutil.copy(src=f"./{file}", dst=f"{self.log_path}/{log_time}/{file}")

    def delete_latest_logs(self) -> None:
        """Delete the latest logs, if the config is set to do so."""
        if self.keep_latest:
            self.logger.info("Keeping top level logs.")
            return
        self._delete_top_level_logs()

    def _delete_top_level_logs(self) -> None:
        """Delete the top level logs (not in logs directory)."""
        for file in self.current_directory.iterdir():
            if file.name.endswith(".log") or file.name[:-2].endswith(".log"):
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
