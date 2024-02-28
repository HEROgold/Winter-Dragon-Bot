
import configparser
import shutil
from collections.abc import Generator
from typing import Any, Self


TEMPLATE_PATH = "./templates/config_template.ini"
CONFIG_PATH = "./config.ini"


class ConfigParserSingleton:
    _instance = None
    config: configparser.ConfigParser

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = configparser.ConfigParser()
        return cls._instance

    def __init__(self) -> None:
        try:
            with open(CONFIG_PATH):
                pass
        except FileNotFoundError as e:
            shutil.copy(TEMPLATE_PATH, CONFIG_PATH)
            to_edit = ["discord_token", "open_api_key", "bot_name", "support_guild_id"]
            msg = f"First time launch detected, please edit the following settings in {CONFIG_PATH}:\n{', '.join(to_edit)}"
            raise ValueError(msg) from e
        self.config.read(CONFIG_PATH)

config = ConfigParserSingleton().config

def is_valid() -> bool:
    for section in config.sections():
        for setting in config.options(section):
            if config[section][setting] == "!!":
                return False
    return True


def get_invalid() -> Generator[str, Any, None]:
    for section in config.sections():
        for setting in config.options(section):
            if config[section][setting] == "!!":
                yield f"{section}:{setting}"


def main() -> None:
    is_valid()


if __name__ == "__main__":
    TEMPLATE_PATH = f".{TEMPLATE_PATH}" # type: ignore
    CONFIG_PATH = f".{CONFIG_PATH}" # type: ignore
    main()
