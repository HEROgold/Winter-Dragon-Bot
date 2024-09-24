from database.engine import engine
from database.tables import *  # noqa: F403
from database.tables.Base import Base


Base().metadata.create_all(engine)
