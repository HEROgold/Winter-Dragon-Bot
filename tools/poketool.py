import logging
import random

import requests

try:
    import config
except ImportError:
    class config:
        class Main:
            BOT_NAME = "TEST"

BASE_URL = "https://pokeapi.co/api/v2"
SPECIES_URL = f"{BASE_URL}/pokemon-species"
ABILITY_URL = f"{BASE_URL}/ability"
POKEMON_URL = f"{BASE_URL}/pokemon"
ITEM_URL = f"{BASE_URL}/item"
TYPE_URL = f"{BASE_URL}/type"
POKEMON_LIMIT_URL = f"{POKEMON_URL}?limit="
ALL_POKEMON_URL = f"{POKEMON_LIMIT_URL}2147483647"
cache = {}

target_database = config.Main.BOT_NAME
logger = logging.getLogger(f"{config.Main.BOT_NAME}.poketool")

# TODO: test and replace json with content.
# TODO: change and use (data)classes


def get_pokemon(pokemon: str | int) -> dict:
    """Get pokemon by their name or id"""
    logger.debug(f"Getting pokemon {pokemon}")
    if pokemon in cache:
        logger.debug(f"ability {pokemon} in cache")
        return cache[pokemon]
    logger.debug(f"requesting ability {pokemon} from api")
    response = requests.get(f"{POKEMON_URL}/{pokemon}")
    data = response.json()
    cache.update(data)
    return data


def get_random_pokemon() -> dict:
    """Get a random pokemon"""
    logger.debug("Getting random pokemon")
    all_pokemon = requests.get(f"{ALL_POKEMON_URL}").json()["results"]
    r_pokemon = random.choice(list(all_pokemon))["name"]
    logger.debug(f"Chose random pokemon {r_pokemon}")
    return get_pokemon(r_pokemon)


def get_ability(ability: str | int) -> dict:
    """Get a pokemon ability by their name or id"""
    logger.debug(f"Getting ability {ability}")
    if ability in cache:
        logger.debug(f"ability {ability} in cache")
        return cache[ability]
    logger.debug(f"requesting ability {ability} from api")
    response = requests.get(f"{ABILITY_URL}/{ability}")
    data = response.json()
    cache.update(data)
    return data


def get_item(item: str | int) -> dict:
    """Get a pokemon Item by their name or id"""
    logger.debug(f"Getting ability {item}")
    if item in cache:
        logger.debug(f"ability {item} in cache")
        return cache[item]
    logger.debug(f"requesting ability {item} from api")
    response = requests.get(f"{ITEM_URL}/{item}")
    data = response.json()
    cache.update(data)
    return data


if __name__ == "__main__":
    print(get_random_pokemon())
