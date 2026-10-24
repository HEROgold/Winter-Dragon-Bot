"""Location of all discord and package related erros go."""
lazy from .api import ApiErrorTree, ApiResponseError, JsonErrorCode


__all__ = [
    "ApiErrorTree",
    "ApiResponseError",
    "JsonErrorCode",
]
