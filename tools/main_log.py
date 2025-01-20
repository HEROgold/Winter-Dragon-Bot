import logging

from bot.src.config import config
from tools.log_manager import LogsManager


bot_logger = logging.getLogger(f"{config['Main']['bot_name']}")
sql_logger = logging.getLogger("sqlalchemy.engine")
discord_logger = logging.getLogger("discord")

logs = LogsManager()

logs.add_logger("bot", bot_logger)
logs.add_logger("discord", discord_logger)
logs.add_logger("sqlalchemy", sql_logger)


stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
bot_logger.addHandler(stream_handler)
