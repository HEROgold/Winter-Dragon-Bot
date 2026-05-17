from __future__ import annotations


class ConfigError(Exception):
    """Base class for all configuration-related exceptions."""


class FirstTimeLaunchError(ConfigError):
    """Raised when it's detected that WinterDragon is launched for the first time."""
