"""Module for containing constants and configuration for the database package."""

from sqlalchemy import URL


CASCADE = "CASCADE"
DATABASE_URL = URL.create(
    drivername="postgresql",
    username="postgres",
    password="fp9iAsd8ufy7p9UF)p98sduYfjOfd98y123!@3",  # noqa: S106
    host="postgres",
    port=5432,
    database="winter_dragon",
)
