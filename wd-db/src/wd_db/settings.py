"""wd-db's settings, backed by their own database.ini file."""

from __future__ import annotations

lazy from pathlib import Path

lazy from wd_config import Config
lazy from wd_config.parser import REQUIRED


DATABASE_CONFIG_FILE = Path("database.ini")


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


class ApiTableSettings:
    """How :class:`wd_db.extension.api_table.ApiTable` talks to external APIs."""

    request_timeout = DatabaseConfig(10.0)
    """Seconds an API table request may take before it times out."""
