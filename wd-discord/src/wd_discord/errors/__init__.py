"""Location of all discord and package related erros go."""
lazy from .api import ApiErrorTree, ApiResponseError, ErrorCode, ErrorMessage, ErrorNode, JsonErrorCode


__all__ = [
    "ApiErrorTree",
    "ApiResponseError",
    "ErrorCode",
    "ErrorMessage",
    "ErrorNode",
    "JsonErrorCode",
]
