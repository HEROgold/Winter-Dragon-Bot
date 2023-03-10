import asyncio
# import pickle
import pickle
import logging

# import pymongo
from pymongo import MongoClient
from pymongo import collection as mcol
from pymongo import database as mdb

import config

# Commented some debug loggers, to filter out spam.
class Database():
    def __init__(self) -> None:
        self.target_database = config.Main.BOT_NAME
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.database")

    async def get_client(self) -> MongoClient:
        IP_PORT = config.Database.IP_PORT
        USER_PASS = config.Database.USER_PASS or "localhost:27017"
        AUTH_METHOD = config.Database.AUTH_METHOD or f"mongodb://{IP_PORT}"
        CONNECTION_STRING = f"mongodb://{USER_PASS}@{IP_PORT}/?authMechanism={AUTH_METHOD}"
        # self.logger.info("Getting MongoClient connection")
        return MongoClient(CONNECTION_STRING)

    async def __get_database__(self, database_name:str) -> mdb.Database:
        mc = await self.get_client()
        # self.logger.debug(f"Getting database: {database_name}")
        return mc.get_database(database_name)

    async def __get_collection__(self, collection_name:str) -> mcol.Collection:
        database = await self.__get_database__(self.target_database)
        self.logger.debug(f"Getting database collection: {collection_name}")
        return database.get_collection(collection_name)

    # HACK:
    # to transform data from MongoDB to python dictionary:
    # list data in l_data > 
    # create valid format using pickle.dumps > 
    # change back to python dict using pickle.loads
    async def get_data(self, collection_name:str) -> dict:
        collection = await self.__get_collection__(collection_name)
        l_data = list(collection.find())
        try:
            d_data = l_data[0]
            del d_data['_id']
            j_data = pickle.dumps(d_data)
            data = pickle.loads(j_data)
        except IndexError:
            self.logger.debug("Returning empty dictionary because no data was found")
            data = {}
        return data

    async def set_data(self, collection_name:str, data:dict) -> None:
        collection = await self.__get_collection__(collection_name)
        try:
            self.logger.debug(f"Updating/replacing data in database: {self.target_database}, in collection: {collection_name}")
            collection.replace_one(filter={}, replacement=data, upsert=True)
        except IndexError:
            self.logger.debug(f"Empty database {collection_name}, inserting data")
            collection.insert_one(data)

async def main() -> None:
    db = Database()
    db.logger.warning("Database.py should only be used for testing!")
    print(await db.get_data("Message"))

if __name__ == "__main__":
    asyncio.run(main())
