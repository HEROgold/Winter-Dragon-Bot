from __future__ import annotations

lazy from confkit import Config as CKConfig

lazy from .constants import CONFIG_FILE


class Config[T](CKConfig[T]):
    """Config descriptor for WinterDragon."""

Config.set_file(CONFIG_FILE)
