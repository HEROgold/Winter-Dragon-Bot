"""System routes for Winter Dragon Bot API.

This module provides system-level endpoints like health checks.
"""

import platform
import time
from typing import Any

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """API health check endpoint.

    Returns:
        Dict[str, Any]: API status information.

    """
    # Return basic system info and status
    return {
        "status": "ok",
        "timestamp": time.time(),
        "version": "0.1.0",
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
    }
