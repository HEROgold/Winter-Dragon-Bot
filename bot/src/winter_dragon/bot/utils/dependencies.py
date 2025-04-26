"""Utilities for handling optional dependencies."""

import importlib.util
import logging
from collections.abc import Callable
from typing import Any, TypeVar


logger = logging.getLogger("winter_dragon.bot.utils.dependencies")

T = TypeVar("T")


def is_package_available(package_name: str) -> bool:
    """Check if a package is available.

    Args:
        package_name: Name of the package to check

    Returns:
        bool: True if the package is available, False otherwise

    """
    return importlib.util.find_spec(package_name) is not None


def optional_dependency(
    package_name: str,
    error_message: str | None = None,
    fallback: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T | Any]]:
    """Decorator to handle optional dependencies.

    Args:
        package_name: Name of the package to check
        error_message: Optional custom error message
        fallback: Value to return if the dependency is missing

    Returns:
        Decorator function

    """
    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            if is_package_available(package_name):
                return func(*args, **kwargs)
            message = error_message or f"Optional package '{package_name}' is required for this feature."
            logger.warning(message)
            if callable(fallback):
                return fallback(*args, **kwargs)
            return fallback
        return wrapper
    return decorator


# Specific dependency checks for common extras
has_beautifulsoup = is_package_available("bs4")
has_requests = is_package_available("requests")
has_fastapi = is_package_available("fastapi")

# Steam dependencies check (requires both BeautifulSoup and requests)
has_steam_dependencies = has_beautifulsoup and has_requests
