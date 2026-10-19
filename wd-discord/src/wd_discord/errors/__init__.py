"""Location of all discord and package related erros go."""
from __future__ import annotations

lazy from .api import ApiErrorTree, ApiResponseError, JsonErrorCode


__all__ = [
    "ApiErrorTree",
    "ApiResponseError",
    "JsonErrorCode",
]
