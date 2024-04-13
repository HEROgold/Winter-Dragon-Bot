
import configparser
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any, Self
from urllib import parse


PROJECT_DIR = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_DIR / "config.ini"

TEMPLATE_PATH = PROJECT_DIR / "templates/"
STATIC_PATH = PROJECT_DIR / "static/"

PERMISSIONS = 70368744177655 # All bot permissions
V10 = "https://discord.com/api/v10"
OAUTH2 = "https://discord.com/api/oauth2"
DISCORD_AUTHORIZE = f"{OAUTH2}/authorize"
DISCORD_OAUTH_TOKEN = f"{OAUTH2}/token"
GET_TOKEN_WEBSITE_URL = parse.quote("http://localhost:5000/get_token")
OAUTH_SCOPE = [
    "relationships.read",
    "guilds.members.read",
    "connections",
    "email",
    "activities.read",
    "identify",
    "guilds",
    "applications.commands",
    "applications.commands.permissions.update"
    "bot",
]


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
