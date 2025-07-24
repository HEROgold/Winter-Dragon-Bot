"""Module for extending SQLModel with custom methods.

This module should make the SQLModel classes more like a `Repository` pattern.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Self

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, Session, select
from sqlmodel import SQLModel as BaseSQLModel
from winter_dragon.database.constants import session as db_session
from winter_dragon.database.errors import AlreadyExistsError, NotFoundError


class BaseModel(BaseSQLModel):
    """Base model class with custom methods."""

    if TYPE_CHECKING:
        id: int | None | Any

    _session: ClassVar[Session] = db_session

    @property
    def session(self) -> Session:
        """Get the current session."""
        return self._session

    def add(self: Self, session: Session | None = None) -> None:
        """Add a record to Database."""
        if self.id is not None:
            msg = f"Record with {self.__class__.__name__}.id={self.id} already exists."
            raise AlreadyExistsError(msg)
        self._create_record(session)

    def update(self: Self, session: Session | None = None) -> None:
        """Create or update a record in Database."""
        session = self._get_session(session)
        if known := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id)
            .with_for_update(),
        ).first():
            return self._update_record(known, session)
        return self._create_record(session)

    @classmethod
    def get(cls, id_: int, session: Session | None = None, *, with_for_update: bool = False) -> Self:
        """Get a record from Database."""
        session = cls._get_session(session)

        if known := session.exec(
            select(cls).where(cls.id == id_).with_for_update()
            if with_for_update
            else select(cls).where(cls.id == id_),
        ).first():
            return known
        msg = f"Record with {cls.__name__}.id={id_} not found."
        raise NotFoundError(msg)

    @classmethod
    def get_all(cls: type[Self], session: Session | None = None) -> Sequence[Self]:
        """Get all records from Database."""
        session = cls._get_session(session)
        return session.exec(select(cls)).all()

    @classmethod
    def _get_session(cls, session: Session | None = None) -> Session:
        if session is None:
            session = cls._session
        return session

    def delete(self, session: Session | None = None) -> None:
        """Delete a record from Database."""
        session = self._get_session(session)
        if known := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id)
            .with_for_update(),
        ).first():
            session.delete(known)
            session.commit()
            return
        msg = f"Record with {self.__class__.__name__}.id={self.id} not found for deletion."
        raise NotFoundError(msg)

    def _create_record(self, session: Session | None = None) -> None:
        session = self._get_session(session)
        session.add(self)
        session.commit()

    def _update_record(self, known: Self, session: Session | None = None) -> None:
        """Update known, with the values from self."""
        session = self._get_session(session)
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


class SQLModel(BaseModel):
    """Base SQLModel class with custom methods."""

    id: int | None = Field(default=None, primary_key=True, index=True)


class DiscordID(BaseModel):
    """Model with a Discord ID as primary key."""

    id: int = Field(sa_column=Column(BigInteger(), primary_key=True))

    @classmethod
    def fetch(cls, id_: int) -> Self:
        """Find existing or create new discord snowflake by id, and return it."""
        session = cls._get_session()
        if user := session.exec(select(cls).where(cls.id == id_)).first():
            return user

        inst = cls(id=id_)
        session.add(inst)
        session.commit()
        return inst
