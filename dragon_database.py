import asyncio
import json
import logging

# import pymongo
from pymongo import MongoClient
from pymongo import collection as mcol
from pymongo import database as mdb

import config


class Database():
    def __init__(self) -> None:
        self.target_database = config.main.database_name
        self.logger = logging.getLogger("winter_dragon.database")

    async def get_client(self) -> MongoClient:
        try:
            IP_PORT = config.database.IP_PORT
            USER_PASS = config.database.USER_PASS
            AUTH_METHOD = config.database.AUTH_METHOD
            CONNECTION_STRING = f"mongodb://{USER_PASS}@{IP_PORT}/?authMechanism={AUTH_METHOD}"
        except Exception as e:
            logging.warning("Defaulting to localhost connection due to error", e)
            IP_PORT = "localhost:27017"
            CONNECTION_STRING = f"mongodb://{IP_PORT}"
        return MongoClient(CONNECTION_STRING)

    async def __get_database__(self, database_name:str) -> mdb.Database:
        MC = await self.get_client()
        return MC.get_database(database_name)

    async def __get_collection__(self, collection_name:str) -> mcol.Collection:
        database = await self.__get_database__(self.target_database)
        return database.get_collection(collection_name)

    # HACK: to transform data from MongoDB to python dictionary:
    # unlist data using l_data > 
    # create valid (string) json format using json.dumps > 
    # change (string) json back to python dict using json.loads
    async def get_data(self, collection_name:str):
        collection = await self.__get_collection__(collection_name)
        l_data = list(collection.find())
        try:
            d_data = l_data[0]
            del d_data['_id']
            j_data = json.dumps(d_data)
            data = json.loads(j_data)
        except IndexError as e:
            self.logger.warning(f"Returning empty dictionary because of the folliwing Error: {e}")
            data = {}
        return data

    async def set_data(self, collection_name:str, data:dict) -> None:
        collection = await self.__get_collection__(collection_name)
        try:
            self.logger.info(f"Updating/replacing data in database: {self.target_database} collection: {collection_name}")
            l_data = list(collection.find())
            d_data = l_data[0]
            print(d_data['_id'])
            collection.replace_one(filter={}, replacement=data, upsert=True)
        except IndexError:
            self.logger.info(f"Empty database {collection_name}, inserting data")
            collection.insert_one(data)

async def main():
    db = Database()
    logging.getLogger(db.logger).warning("Database.py should only be used for testing!")
    mc = await db.get_client()
    print(await db.get_data("Message"))

if __name__ == "__main__":
    asyncio.run(main())
