"""wd-db's settings, backed by their own database.ini file."""

lazy from wd_config import Config
lazy from wd_config.constants import DATABASE_CONFIG_FILE
lazy from wd_config.parser import REQUIRED


class DatabaseConfig[T](Config[T]):
    """Config descriptor scoped to the database settings file."""


DatabaseConfig.bind(DATABASE_CONFIG_FILE, operator=True)


class DbUrl:
    """The database URL components; ``wd_db.constants.DATABASE_URL`` is assembled from them."""

    driver_name = DatabaseConfig("postgresql")
    database = DatabaseConfig("winter_dragon")
    username = DatabaseConfig("postgres")
    password = DatabaseConfig(REQUIRED)
    """The database user's password; the operator fills it in."""
    host = DatabaseConfig("postgres")
    port = DatabaseConfig(5432)

