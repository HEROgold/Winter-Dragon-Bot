import logging

from config import config


class LoggerMixin:
    def __init_subclass__(cls, *args, **kwargs) -> None:
        super().__init_subclass__(*args, **kwargs)
        cls.logger = logging.getLogger(f"{config['Main']['bot_name']}.{cls.__class__.__name__}")
