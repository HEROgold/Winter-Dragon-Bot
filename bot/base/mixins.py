import logging
from typing import Any

from config import config


class LoggerMixin:
    logger: logging.Logger
    _furthest_child_name = None  # Track the name of the furthest child class

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init_subclass__(**kwargs)
        # Update the furthest child name with the current subclass name
        LoggerMixin._furthest_child_name = cls.__name__
        # Update the logger for all classes in the hierarchy to reflect the furthest child
        cls.update_logger_for_hierarchy()

    @classmethod
    def update_logger_for_hierarchy(cls) -> None:
        # Traverse the MRO (Method Resolution Order) in reverse to update logger from base to the furthest child
        for base in reversed(cls.mro()):
            if issubclass(base, LoggerMixin) and hasattr(base, "_furthest_child_name"):
                base.logger = logging.getLogger(f"{config['Main']['bot_name']}.{LoggerMixin._furthest_child_name}")
