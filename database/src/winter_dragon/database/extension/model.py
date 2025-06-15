"""Module for extending SQLModel with custom methods."""

from typing import Self

from sqlmodel import Session, select
from sqlmodel import SQLModel as BaseSQLModel
from winter_dragon.database.errors import AlreadyExistsError, NotFoundError


class SQLModel(BaseSQLModel):
    """Base SQLModel class with custom methods."""

    id: int | None

    def add(self: Self, session: Session) -> None:
        """Add a record to Database."""
        if self.id is not None:
            msg = f"Record with {self.__class__.__name__}.id={self.id} already exists."
            raise AlreadyExistsError(msg)
        self._create_record(session)

    def update(self: Self, session: Session) -> None:
        """Create or update a record in Database."""
        if known := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id)
            .with_for_update(),
        ).first():
            return self._update_record(known, session)
        return self._create_record(session)

    def delete(self, session: Session) -> None:
        """Delete a record from Database."""
        if known := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id)
            .with_for_update(),
        ).first():
            session.delete(known)
            session.commit()
        else:
            msg = f"Record with {self.__class__.__name__}.id={self.id} not found for deletion."
            raise NotFoundError(msg)

    def _create_record(self, session: Session) -> None:
        session.add(self)
        session.commit()

    def _update_record(self, known: Self, session: Session) -> None:
        for field, value in self.model_fields.items():
            if field == "id":
                continue
            # Get the actual value from the instance, and not field info
            # Use value.annotation to match the types.
            if value.annotation is type(self.__dict__[field]):
                setattr(known, field, self.__dict__[field])
            else:
                msg = f"Field {field=} has wrong type: {value.annotation} != {type(self.__dict__[field])}"
                raise TypeError(msg)
        session.add(known)
        session.commit()
