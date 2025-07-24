"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, status
from winter_dragon.database.extension.model import BaseModel


if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO:
# Ensure that the requests are authenticated and authorized.
# Right now anyone can put a random ID into the object, and change the data related to that ID.
# Even if that ID was not given out to that requesting user.

class APIModel[T: type[BaseModel]]:
    """Base APIModel class with custom methods for API interactions."""

    router: APIRouter = APIRouter(tags=["APIModel"])

    def __init__(self, model: T) -> None:
        """Initialize the APIModel with a SQLModel instance."""
        self.model = model
        self.router.tags.append(model.__class__.__name__)
        self.router.prefix = f"/{model.__class__.__name__.lower()}"

    @router.get("/{_id}")
    def get(self, _id: int) -> T | int:
        """Get a record by ID."""
        return self.model.get(_id) or status.HTTP_404_NOT_FOUND

    @router.delete("/{_id}")
    def delete(self, _id: int) -> None:
        """Delete a record by ID."""
        inst = self.model.get(_id)
        self.model.delete(inst)

    @router.get("/")
    def get_all(self) -> Sequence[T]:
        """Get all records."""
        return self.model.get_all()

    @router.post("/")
    def create(self, item: T) -> T:
        """Create a new record."""
        self.model.add(item)
        return item

    @router.put("/")
    def update(self, item: T) -> None | int:
        """Update an existing record."""
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        self.model.update(item)
        return None
