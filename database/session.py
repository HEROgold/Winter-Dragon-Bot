from sqlalchemy.orm import Session

from database.engine import engine


session = Session(engine)
