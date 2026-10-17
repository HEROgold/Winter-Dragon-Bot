"""The app's own config scopes: cog settings in ``cogs.ini``."""

from __future__ import annotations

lazy from pathlib import Path

lazy from wd_config import Config


COGS_CONFIG_FILE = Path("cogs.ini")


class CogConfig[T](Config[T]):
    """Config descriptor scoped to the cog settings file; every cog shares it, one section per settings class."""


CogConfig.bind(COGS_CONFIG_FILE, operator=True)
