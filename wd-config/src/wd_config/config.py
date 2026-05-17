from __future__ import annotations

from confkit import Config as CKConfig

from .constants import CONFIG_FILE


class Config[T](CKConfig[T]):
    """Config descriptor for WinterDragon."""

    FILE = CKConfig(CONFIG_FILE)

Config.set_file(Config.FILE)
