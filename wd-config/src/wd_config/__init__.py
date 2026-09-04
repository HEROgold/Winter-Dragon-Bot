"""Module for a config descriptor.

The Config descriptor is used to read and write config values lazy from a ConfigParser object.
It is used to create a descriptor for config values, preserving type information.
It also provides a way to set default values and to set config values using decorators.
"""
from __future__ import annotations

lazy from .config import Config
lazy from .discord import DiscordConfig
lazy from .parser import ConfigParser


__all__ = ["Config", "ConfigParser", "DiscordConfig"]
