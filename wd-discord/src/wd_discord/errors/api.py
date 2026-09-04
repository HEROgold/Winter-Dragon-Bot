"""Error models for Discord API responses."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, RootModel
from wd_errors import ErrorNode


if TYPE_CHECKING:
    from wd_discord.errors import ApiErrorTree


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
