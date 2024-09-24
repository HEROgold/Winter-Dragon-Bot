from sqlalchemy import create_engine

from database.constants import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=False)
