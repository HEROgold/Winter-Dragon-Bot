"""Error models for Discord API responses."""
from __future__ import annotations

lazy from enum import IntEnum
lazy from typing import TYPE_CHECKING

lazy from pydantic import BaseModel, RootModel
lazy from wd_errors import ErrorNode


if TYPE_CHECKING:
    lazy from wd_discord.errors import ApiErrorTree


class JsonErrorCode(IntEnum):
    """Codes Discord puts in a failed response's ``code`` (https://docs.discord.com/developers/topics/opcodes-and-status-codes#json)."""

    GENERAL_ERROR = 0
    """Discord's catch-all; wd-discord also uses it for a response it couldn't read."""
    UNKNOWN_CHANNEL = 10003
    """The channel doesn't exist, e.g. it was deleted already."""
    UNKNOWN_GUILD = 10004
    UNKNOWN_MEMBER = 10007
    """The user isn't a member of the guild (any more)."""
    UNKNOWN_MESSAGE = 10008
    UNKNOWN_OVERWRITE = 10009
    UNKNOWN_ROLE = 10011
    UNKNOWN_USER = 10013
    TARGET_NOT_IN_VOICE = 40032
    """The member to move isn't connected to voice."""
    MISSING_ACCESS = 50001
    """The bot can't see the resource, e.g. it lacks VIEW_CHANNEL on the channel."""
    CANNOT_DM_USER = 50007
    """The user doesn't accept direct messages from the bot."""
    MISSING_PERMISSIONS = 50013
    """The bot can see the resource but lacks a permission the action needs."""


class ApiErrorTree(RootModel[ErrorNode | dict[str, "ApiErrorTree"]]):
    """Represents the entire error tree, which can be a single node or a dictionary of child nodes."""

    root: ErrorNode | dict[str, ApiErrorTree]

    def __iter__(self):
        """Iterate over all error messages in the tree."""
        match self.root:
            case ErrorNode() as node:
                yield from node.errors_list
            case dict() as children:
                for child in children.values():
                    yield from child

ApiErrorTree.model_rebuild()

UNKNOWN_RANGE = range(10001, 20000)
"""Discord's codes for "Unknown <resource>": what the request named doesn't exist."""


class ApiResponseError(BaseModel):
    """The final model that can parse all three variants.

    ``errors`` is optional: simple failures (e.g. ``401: Unauthorized``) return only
    ``code`` and ``message`` without a per-field error tree.
    """

    code: int
    """Discord's JSON error code; see :class:`JsonErrorCode` for the ones wd-discord names."""
    message: str
    errors: ApiErrorTree | None = None
    status: int = 0
    """The HTTP status of the response; 0 when no response arrived (e.g. rate-limit retries ran out)."""

    @property
    def unknown_resource(self) -> bool:
        """Whether the request named something that doesn't exist (any more): Discord's 10xxx "Unknown ..." codes."""
        return UNKNOWN_RANGE.start <= self.code < UNKNOWN_RANGE.stop
