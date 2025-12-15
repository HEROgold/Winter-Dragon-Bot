
"""
Winter-Dragon API extension initialization.
This module requires the optional 'winter-dragon[api]' package to be installed.
"""
import warnings
from importlib.util import find_spec


def check_api_dependencies() -> bool | None:
    """Check if the required API dependencies are installed."""
    try:
        find_spec("fastapi")
        find_spec("uvicorn")
    except ImportError:
        warnings.warn(
            "The API functionality requires additional dependencies. Please install them using: pip install winter-dragon[api]",
            ImportWarning,
            stacklevel=2,
        )
        return False
    else:
        return True


# Perform the check when the module is imported
API_AVAILABLE = check_api_dependencies()
