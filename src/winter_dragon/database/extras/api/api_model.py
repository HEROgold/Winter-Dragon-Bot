"""Module that provides a base APIModel class for API interactions with SQLModel instances."""

import logging
from collections.abc import Sequence

from fastapi import APIRouter, status

from winter_dragon.database.extension.model import BaseModel


class APIModel[T: type[BaseModel]]:
    """Base APIModel class with custom methods for API interactions."""

    def __init__(self, model: T, router: APIRouter) -> None:
        """Initialize the APIModel with a SQLModel instance, adding routes to the provided router."""
        self.model = model
        self.router = router
        self.router.tags = [model.__name__, *self.router.tags]
        self.router.add_api_route("/", self.get_all, methods=["GET"])
        self.router.add_api_route("/{_id}", self.get, methods=["GET"])
        self.router.add_api_route("/{item}", self.create, methods=["POST"])
        self.router.add_api_route("/{item}", self.update, methods=["PUT"])
        self.router.add_api_route("/{_id}", self.delete, methods=["DELETE"])

    def get_all(self) -> Sequence[T]:
        """Get all records."""
        self.model.logger = logging.getLogger(self.model.__name__)
        return self.model.get_all()

    def get(self, _id: int) -> T | int:
        """Get a record by ID."""
        self.model.logger = logging.getLogger(self.model.__name__)
        return self.model.get(_id) or status.HTTP_404_NOT_FOUND

    def create(self, item: T) -> T:
        """Create a new record."""
        self.model.logger = logging.getLogger(self.model.__name__)
        self.model.add(item)
        return item

    def update(self, item: T) -> None | int:
        """Update an existing record."""
        self.model.logger = logging.getLogger(self.model.__name__)
        if not item.id or not self.model.get(item.id):
            return status.HTTP_404_NOT_FOUND
        self.model.update(item)
        return None

    def delete(self, _id: int) -> None:
        """Delete a record by ID."""
        self.model.logger = logging.getLogger(self.model.__name__)
        inst = self.model.get(_id)
        self.model.delete(inst)
