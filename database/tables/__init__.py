from collections.abc import AsyncGenerator

from sqlalchemy import (
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
)


CASCADE = "CASCADE"
DATABASE_URL = "sqlite:///database/db.sqlite"

engine = create_engine(DATABASE_URL, echo=False)
session = Session(engine)
async_engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    "Subclass of DeclarativeBase with customizations."

    def __repr__(self) -> str:
        return str(self.__dict__)


all_tables = Base.__subclasses__()


Base().metadata.create_all(engine)



async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session



# TODO: Test using Hypothesis
# https://youtu.be/dsBitCcWWf4
