from pydantic_settings import BaseSettings

from bot.config import config


class Settings(BaseSettings):
    app_name: str = config["Main"]["bot_name"]
    SECRET_KEY: str = config["Tokens"]["client_secret"]
