from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.constants import DATABASE_URL
from database.tables import *  # noqa: F403
from database.tables.base import Base


engine = create_engine(DATABASE_URL, echo=False)


Base().metadata.create_all(engine)
session = Session(engine)
