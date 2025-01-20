import configparser
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any, Self

from constants import WEBSITE_CONFIG, WEBSITE_DIR


class ConfigParserSingleton(configparser.ConfigParser):
    _instance = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        try:
            with Path(WEBSITE_CONFIG).open():
                pass
        except FileNotFoundError as _:
            shutil.copy(WEBSITE_DIR / "config_template.ini", WEBSITE_CONFIG)
        self.read(WEBSITE_CONFIG)

    def is_valid(self) -> bool:
        for section in config.sections():
            for setting in config.options(section):
                if self[section][setting] == "!!":
                    return False
        return True

    def get_invalid(self) -> Generator[str, Any]:
        for section in self.sections():
            for setting in self.options(section):
                if self[section][setting] == "!!":
                    yield f"{section}:{setting}"


config = ConfigParserSingleton()
