import configparser
import shutil
from collections.abc import Generator
from typing import Any, Self

from bot.constants import BOT_CONFIG, BOT_DIR
from bot.errors import FirstTimeLaunchError


class ConfigParserSingleton(configparser.ConfigParser):
    _instance = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        try:
            with BOT_CONFIG.open():
                pass
        except FileNotFoundError as e:
            shutil.copy(BOT_DIR/"config_template.ini", BOT_CONFIG)
            to_edit = ["discord_token", "open_api_key", "bot_name", "support_guild_id"]
            msg = f"First time launch detected, please edit the following settings in {BOT_CONFIG}:\n{', '.join(to_edit)}"
            raise FirstTimeLaunchError(msg) from e
        self.read(BOT_CONFIG)

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
# TODO @HEROgold: Split non-bot configs into their owner config files
# 138
