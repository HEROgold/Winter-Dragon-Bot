import logging
from typing import Optional

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker

# try:
    # import config
# except ModuleNotFoundError:
# TEMP DATA
class config:
    class Main:
        BOT_NAME:str = "winter_dragon" # Name of the MongoDatabase
        
    class Database:
        PERIODIC_CLEANUP:bool = True # allow periodic cleanups of the database (mongodb or the file's)
        IP_PORT:str = "localhost:3306"
        USER_PASS:str = "winterdragon:ryJKD90i6Pmbmc3A"
        AUTH_METHOD:str = "SCRAM-SHA-256"


class Database:
    DATABASE_NAME = config.Main.BOT_NAME
    engine: sqlalchemy.Engine = None
    connection: sqlalchemy.Connection = None
    session_maker:sessionmaker = None
    session = None

    def __init__(self) -> None:
        self.logger = logging.getLogger(
            f"{config.Main.BOT_NAME}.{self.__class__.__name__}"
        )
        self.engine = self._get_engine(self.DATABASE_NAME)
        self.connection: sqlalchemy.Connection = self._connect(engine=self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
        self.session = self.session_maker()

    def _get_engine(self, database_name: str = None) -> sqlalchemy.Engine:
        login = config.Database.USER_PASS.split(sep=":")
        if database_name:
            return sqlalchemy.create_engine(
                f"mysql+mysqlconnector://{login[0]}:{login[1]}@{config.Database.IP_PORT}/{self.DATABASE_NAME}",
                echo=True,
                connect_args={'connect_timeout': 5}
            )
        else:
            return sqlalchemy.create_engine(
                f"mysql+mysqlconnector://{login[0]}:{login[1]}@{config.Database.IP_PORT}",
                echo=True,
                connect_args={'connect_timeout': 5}
            )

    def _connect(self, engine: sqlalchemy.Engine) -> None:
        """Connect to a database, or create one if it doesn't exist. Needs to be closed manually

        Args:
            engine (sqlalchemy.Engine): 
        """
        self.logger.debug(f"Getting connection to database: {self.DATABASE_NAME}")
        if not self.engine:
            engine = self._get_engine(database_name=self.DATABASE_NAME)
        try:
            self.connection = engine.connect()
        except ProgrammingError as e:
            for arg in e.args:
                if "Unknown database" in arg:
                    break
            else:
                raise e
            self._get_engine().connect().execute(
                text(f"CREATE DATABASE {self.DATABASE_NAME}")
            )
            self.connection = self._connect(engine)

    def get_all_data(self, table_name: str) -> Optional[list[set]]:
        """Get all data from a table, and handles the database connection

        Args:
            table_name (str): Name of the table to get data from

        Returns:
            list[set]: List of all data/rows in the table
        """
        if not self.engine:
            self._get_engine(database_name=self.DATABASE_NAME)
        if not self.connection:
            self._connect(self.engine)
        try:
            results = self.connection.execute(text(f"SELECT * FROM {table_name}"))
            self.logger.debug(f"Returning Table {table_name} contents")
        except ProgrammingError as e:
            for arg in e.args:
                if "Table" in arg and "doesn't exist" in arg:
                    self.logger.warning(
                        f"Returning None, Table {table_name} doesn't exist!"
                    )
                    self.connection.close()
                    return None
        self.connection.close()
        return results.all()

def main() -> None:
    db = Database()
    db.logger.warning("Database.py should only be used for testing or importing!")
    if data := db.get_all_data("Test"):
        for i in data:
            print(i)


if __name__ == "__main__":
    main()
