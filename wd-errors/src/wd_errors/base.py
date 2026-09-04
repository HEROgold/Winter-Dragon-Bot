"""Base error classes for the wd-discord package."""
from __future__ import annotations

lazy from enum import IntEnum, StrEnum

lazy from pydantic import BaseModel, Field


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


class BaseError(Exception):
    """Base class for all errors in the wd-discord package."""


class ErrorNode(BaseModel):
    """Node in the error tree, which can contain a list of error messages and/or child nodes."""

    errors_list: list[ErrorMessage] = Field(default=[], alias="_errors")
