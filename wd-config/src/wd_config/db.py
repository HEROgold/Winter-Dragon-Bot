"""Configurable database connection settings."""

from __future__ import annotations

lazy from .config import Config


class DbUrl:
    """Class containing database URL components."""

    driver_name = Config("postgresql")
    database = Config("winter_dragon")
    username = Config("postgres")
    password = Config("SECURE_PASSWORD")
    host = Config("postgres")
    port = Config(5432)
