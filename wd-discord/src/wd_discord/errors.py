"""Location of all discord and package related erros go."""
from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel, Field, RootModel


class BaseError(Exception):
    """Base class for all errors in the wd-discord package."""

class ErrorCode(StrEnum):
    """Various error codes that can be returned by the Discord API."""

    BASE_TYPE_CHOICES = "BASE_TYPE_CHOICES"
    BASE_TYPE_REQUIRED = "BASE_TYPE_REQUIRED"
    APPLICATION_COMMAND_TOO_LARGE = "APPLICATION_COMMAND_TOO_LARGE"


class Platform(StrEnum):
    """Platform a user is using to access Discord."""

    DESKTOP = "desktop"
    ANDROID = "android"
    IOS = "ios"


class Activity(IntEnum):
    """Activity a user is engaged in on Discord."""

    PLAYING = 0
    STREAMING = 1
    LISTENING = 2
    WATCHING = 3
    CUSTOM = 4
    COMPETING = 5


class ErrorMessage(BaseModel):
    """Error message with a code and a message string."""

    code: ErrorCode
    message: str


class ErrorNode(BaseModel):
    """Node in the error tree, which can contain a list of error messages and/or child nodes."""

    errors_list: list[ErrorMessage] = Field(default=[], alias="_errors")


class ApiErrorTree(RootModel[ErrorNode | dict[str, "ApiErrorTree"]]):
    """Represents the entire error tree, which can be a single node or a dictionary of child nodes."""

    root: ErrorNode | dict[str, ApiErrorTree]

ApiErrorTree.model_rebuild()


class ApiResponseError(BaseModel):
    """The final model that can parse all three variants.

    ``errors`` is optional: simple failures (e.g. ``401: Unauthorized``) return only
    ``code`` and ``message`` without a per-field error tree.
    """

    code: int
    message: str
    errors: ApiErrorTree | None = None
