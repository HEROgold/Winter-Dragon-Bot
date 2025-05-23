from typing import Self

from sqlmodel import Session, select
from sqlmodel import SQLModel as BaseSQLModel


class SQLModel(BaseSQLModel):
    """Base SQLModel class with custom methods."""

    id: int | None

    def update(self: Self, session: Session) -> None:
        """Create or update a sale record in Database."""
        if known := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id)
            .with_for_update(),
        ).first():
            return self._update_record(known, session)
        return self._create_record(session)

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
