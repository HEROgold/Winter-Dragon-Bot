# TODO: create a wrapper, that's importable, logs it own location (extension/cog/function)
# which logs all errors happening in events (unhandled by error.py)

# TODO: Needs testing

from asyncio import iscoroutinefunction
import inspect
import logging
from types import FunctionType

from .config_reader import config


def event_logger(func: FunctionType):
    logger: logging.Logger = func.__class__.__dict__.get("logger", logging.getLogger(f"{config['Main']['bot_name']}.event_errors"))
    logger.debug(f"Wrap! {inspect.getfile(func)}, in {func.__class__} at {func.__name__}")

    async def async_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {inspect.getfile(func)}, in {func.__class__} at {func.__name__}:\n{e}")
            
            logger.exception(f"Error in {inspect.getfile(func)}, in {func.__class__} at {func.__name__}:\n{e}")

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {inspect.getfile(func)}, in {func.__class__} at {func.__name__}:\n{e}")
            logger.exception(f"Error in {inspect.getfile(func)}, in {func.__class__} at {func.__name__}:\n{e}")

    return async_wrapper if iscoroutinefunction(func) else wrapper
