"""Utilities for handling optional dependencies."""

import importlib.util
import logging


logger = logging.getLogger("winter_dragon.bot.utils.dependencies")


def is_package_available(package_name: str) -> bool:
    """Check if a package is available.

    Args:
        package_name: Name of the package to check

    Returns:
        bool: True if the package is available, False otherwise

    """
    return importlib.util.find_spec(package_name) is not None


# Specific dependency checks for common extras
has_beautifulsoup = is_package_available("bs4")
has_requests = is_package_available("requests")
has_fastapi = is_package_available("fastapi")

# Steam dependencies check (requires both BeautifulSoup and requests)
has_steam_dependencies = has_beautifulsoup and has_requests
