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

    UNKNOWN_CHANNEL = 10003
    """The channel doesn't exist, e.g. it was deleted already."""
    MISSING_ACCESS = 50001
    """The bot can't see the resource, e.g. it lacks VIEW_CHANNEL on the channel."""
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

class ApiResponseError(BaseModel):
    """The final model that can parse all three variants.

    ``errors`` is optional: simple failures (e.g. ``401: Unauthorized``) return only
    ``code`` and ``message`` without a per-field error tree.
    """

    code: int
    message: str
    errors: ApiErrorTree | None = None
