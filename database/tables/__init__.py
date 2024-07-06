from sqlalchemy import (
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
)


engine = create_engine("sqlite:///database/db.sqlite", echo=False)
session = Session(engine)
CASCADE = "CASCADE"


class Base(DeclarativeBase):
    "Subclass of DeclarativeBase with customizations."

    def __repr__(self) -> str:
        return str(self.__dict__)


all_tables = Base.__subclasses__()


Base().metadata.create_all(engine)


# TODO: Test using Hypothesis
# https://youtu.be/dsBitCcWWf4
